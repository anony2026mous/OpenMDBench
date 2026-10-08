"""Build the complete IE matrix document: force laydown + every recorded metric.

Combines two authoritative sources:

  * the scenario packages (``scenarios/formal/ie_0*/scenario.yaml`` and
    ``agents.yaml``) for the enemy/friendly laydown, and
  * the exported result set (``_w1_runs/ie_set_results_<tag>.json``) for the
    scorecard layers and every raw metric recorded per episode.

Writes ``ie_set_matrix_<tag>.md`` next to this script.

Usage:
    python _w1_ie_report.py --tag s1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

SCENARIOS = [
    ("IE-01-SINGLE-TARGET", "ie_01_single_target", "单目标拦截"),
    ("IE-02-DUAL-THREAT", "ie_02_dual_threat", "双威胁防御"),
    ("IE-03-SURFACE-RAID", "ie_03_surface_raid", "水面突袭"),
    ("IE-04-COMBINED-ARMS", "ie_04_combined_arms", "联合兵种攻击"),
    ("IE-05-MULTI-AXIS", "ie_05_multi_axis", "多方向接近"),
    ("IE-06-DECOY-MIXED", "ie_06_decoy_mixed", "真假威胁与诱导攻击"),
    ("IE-07-CROSS-DOMAIN", "ie_07_cross_domain", "跨域渗透"),
    ("IE-08-ISLAND-STRIKE", "ie_08_island_strike", "岛礁突击"),
]
ARMS = ("rule", "hybrid-llm", "pure-llm")
ARM_KEY = {"rule": "rule", "hybrid-llm": "llm", "pure-llm": "purellm"}


def load_scenario(package: str) -> tuple[dict, dict]:
    base = ROOT / "scenarios" / "formal" / package
    scenario = yaml.safe_load((base / "scenario.yaml").read_text(encoding="utf-8"))
    agents = yaml.safe_load((base / "agents.yaml").read_text(encoding="utf-8"))
    return (scenario.get("scenario") or scenario), agents


def laydown(scenario: dict, agents: dict) -> dict:
    def entities() -> list[dict]:
        found = [e for e in scenario.get("entities", ()) if isinstance(e, dict)]
        for event in scenario.get("events", ()) or ():
            if isinstance(event, dict) and event.get("event_type") == "spawn":
                blueprint = (event.get("payload") or {}).get("entity")
                if isinstance(blueprint, dict):
                    found.append(blueprint)
        return found

    every = entities()
    red = [e for e in every if e["faction_id"] == "coalition.intruder"]
    blue = [e for e in every if e["faction_id"] == "coalition.defender"]

    def has(entity: dict, token: str) -> bool:
        return token in {str(t) for t in entity.get("tags", ()) or ()}

    red_uav = [e for e in red if has(e, "uav") and not has(e, "decoy")]
    red_decoy = [e for e in red if has(e, "decoy")]
    red_boat = [e for e in red if has(e, "boat")]
    blue_uav = [e for e in blue if has(e, "interceptor")]
    blue_usv = [e for e in blue if has(e, "usv") and not has(e, "facility")]
    facilities = [e for e in blue if has(e, "facility")]
    sensors = [e for e in blue if has(e, "sensor-site")]

    def ingress(units: list[dict]) -> str:
        if not units:
            return "—"
        xs = sorted(float(e["initial_state"]["position_m"][0]) for e in units)
        return f"{xs[0]/1000:.0f}–{xs[-1]/1000:.0f} km"

    def ammo_of(units: list[dict]) -> str:
        values = {sum(e.get("ammunition", {}).values()) for e in units}
        return "/".join(str(int(v)) for v in sorted(values)) or "—"

    waves = {}
    for event in scenario.get("events", ()) or ():
        if isinstance(event, dict) and event.get("event_type") == "spawn":
            tick = (event.get("trigger") or {}).get("tick")
            waves[tick] = waves.get(tick, 0) + 1

    return {
        "red_uav": len(red_uav), "red_decoy": len(red_decoy), "red_boat": len(red_boat),
        "red_total": len(red),
        "red_ingress": ingress(red_uav + red_boat),
        "red_waves": ", ".join(f"t={t}:{c}" for t, c in sorted(waves.items())) or "全程在场",
        "blue_uav": len(blue_uav), "blue_usv": len(blue_usv),
        "blue_total_combat": len(blue_uav) + len(blue_usv),
        "blue_uav_ammo": ammo_of(blue_uav), "blue_usv_ammo": ammo_of(blue_usv),
        "facilities": len(facilities),
        "facility_weights": json.dumps(agents.get("facility_weights") or {},
                                       ensure_ascii=False),
        "shore_sensors": len(sensors),
        "duration": (scenario.get("world") or {}).get("duration_ticks"),
        "horizon_tick": (scenario.get("world") or {}).get("duration_ticks"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="s1")
    args = parser.parse_args()

    payload = json.loads((RUNS / f"ie_set_results_{args.tag}.json").read_text("utf-8"))
    rows = {(r["arm"], r["scenario"]): r for r in payload["rows"]}

    out: list[str] = []
    add = out.append
    add(f"# IE 拦截交战场景集：完整实验矩阵（tag={args.tag}）\n")
    add("> seed 7；`--plan-interval 10`；`--frontend graph`（两个 LLM 臂）。")
    add("> 三臂：`rule` = 规则规划 + GOAI 执行；`hybrid-LLM` = 千问规划 + GOAI 执行；"
        "`pure-LLM` = 每 tick 直接出低层指令。")
    add("> **配色约定**：`coalition.intruder`（红 / 威胁方）vs "
        "`coalition.defender`（蓝 / 我方）。\n")

    # ---------------- 1. laydown -----------------------------------------
    add("## 1. 敌我双方配置\n")
    add("| 场景 | 威胁无人机 | 威胁诱饵 | 威胁自爆船 | 威胁合计 | 来袭距离 | 波次 | "
        "我方无人机 | 我方无人船 | 我方作战单元 | 岸基传感器 | 受保护设施 | 时长 |")
    add("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    configs = {}
    for public_id, package, zh in SCENARIOS:
        scenario, agents = load_scenario(package)
        info = laydown(scenario, agents)
        configs[public_id] = info
        add(f"| **{public_id}**<br>{zh} | {info['red_uav']} | {info['red_decoy']} | "
            f"{info['red_boat']} | **{info['red_total']}** | {info['red_ingress']} | "
            f"{info['red_waves']} | {info['blue_uav']} | {info['blue_usv']} | "
            f"**{info['blue_total_combat']}** | {info['shore_sensors']} | "
            f"{info['facilities']} | {info['duration']} |")

    add("\n### 1.1 弹药预算与受保护设施权重\n")
    add("| 场景 | 我方无人机载弹 | 我方无人船载弹 | 设施权重 |")
    add("|---|---|---|---|")
    for public_id, _p, _zh in SCENARIOS:
        info = configs[public_id]
        add(f"| {public_id} | {info['blue_uav_ammo']} | {info['blue_usv_ammo']} | "
            f"{info['facility_weights'] or '—'} |")

    # ---------------- 2. overall matrix ----------------------------------
    add("\n## 2. 总体策略评分矩阵（防守方视角，越高越好）\n")
    add("| 场景 | rule | hybrid-LLM | pure-LLM | 胜者 | 领先幅度 |")
    add("|---|---|---|---|---|---|")
    tally = {a: {"win": 0, "loss": 0, "tie": 0, "sum": 0.0} for a in ARMS}
    for public_id, _p, zh in SCENARIOS:
        scores = {a: rows.get((a, public_id), {}).get("defender_score") for a in ARMS}
        present = {a: v for a, v in scores.items() if isinstance(v, (int, float))}
        best = max(present, key=lambda k: present[k]) if present else None
        ordered = sorted(present.values(), reverse=True)
        margin = (ordered[0] - ordered[1]) if len(ordered) > 1 else 0.0
        for arm in ARMS:
            if arm not in present or best is None:
                continue
            delta = present[arm] - present["rule"]
            tally[arm]["sum"] += delta
            tally[arm]["win" if delta > 0.005 else ("loss" if delta < -0.005 else "tie")] += 1
        cells = " | ".join(
            (f"**{scores[a]:.4f}**" if a == best else f"{scores[a]:.4f}")
            if isinstance(scores[a], (int, float)) else "—" for a in ARMS)
        add(f"| **{public_id}** | {cells} | {best} | {margin:.4f} |")

    add("\n**汇总**\n")
    add("| 臂 | 胜 | 平 | 负 | 平均差额 vs rule |")
    add("|---|---|---|---|---|")
    for arm in ARMS:
        t = tally[arm]
        played = t["win"] + t["loss"] + t["tie"]
        add(f"| {arm} | {t['win']} | {t['tie']} | {t['loss']} | "
            f"{t['sum'] / played:+.4f} |" if played else f"| {arm} | — | — | — | — |")

    # ---------------- 3. layers ------------------------------------------
    add("\n## 3. 逐层得分（每场景每臂）\n")
    layers = ("terminal", "facilities", "depth", "leak", "exchange", "ammo", "surface")
    add("| 场景 | 臂 | 总分 | " + " | ".join(layers) + " |")
    add("|---|---|---|" + "---|" * len(layers))
    for public_id, _p, _zh in SCENARIOS:
        for arm in ARMS:
            row = rows.get((arm, public_id))
            if row is None:
                continue
            cells = " | ".join(
                f"{row.get('layer_' + name):.2f}"
                if isinstance(row.get("layer_" + name), (int, float)) else "—"
                for name in layers)
            add(f"| {public_id} | {arm} | {row['defender_score']:.4f} | {cells} |")

    # ---------------- 4. raw metrics -------------------------------------
    add("\n## 4. 全部记录指标（每场景每臂）\n")
    metric_groups = [
        ("终局", [("outcome", "终局判定"), ("terminal_tick", "锁定 tick"),
                  ("ticks_run", "实跑 tick"), ("aborted", "中断")]),
        ("交战", [("fires_total", "执行发射总数"), ("fires_blue", "我方发射"),
                  ("fires_red", "威胁方发射"), ("interception_rate", "拦截率"),
                  ("release_rate", "投弹率"), ("leak_rate", "漏防率"),
                  ("deep_rate", "纵深拦截率"),
                  ("interception_depth_mean_m", "纵深均值 m"),
                  ("interception_depth_median_m", "纵深中位 m")]),
        ("战损", [("uav_lost_blue", "我方无人机损失"), ("uav_total_blue", "我方无人机总数"),
                  ("usv_lost_blue", "我方无人船损失"), ("usv_total_blue", "我方无人船总数"),
                  ("uav_lost_red", "威胁无人机损失"), ("uav_total_red", "威胁无人机总数"),
                  ("usv_lost_red", "威胁自爆船损失"), ("usv_total_red", "威胁自爆船总数")]),
        ("效率与目标", [("defender_kills", "我方击杀"), ("attacker_kills", "我方被击杀"),
                        ("ammo_efficiency", "杀伤/发"),
                        ("facility_survival", "设施加权存活"),
                        ("facilities_destroyed", "设施摧毁数")]),
        ("被拒原因与耗时", [("fire_rejections", "开火拒绝原因"),
                            ("elapsed_seconds", "用时 s")]),
    ]
    for title, fields in metric_groups:
        add(f"\n### 4.{metric_groups.index((title, fields)) + 1} {title}\n")
        add("| 场景 | 臂 | " + " | ".join(label for _k, label in fields) + " |")
        add("|---|---|" + "---|" * len(fields))
        for public_id, _p, _zh in SCENARIOS:
            for arm in ARMS:
                row = rows.get((arm, public_id))
                if row is None:
                    continue
                cells = []
                for key, _label in fields:
                    value = row.get(key)
                    if isinstance(value, float):
                        value = f"{value:.4f}"
                    elif value is None:
                        value = "—"
                    cells.append(str(value))
                add(f"| {public_id} | {arm} | " + " | ".join(cells) + " |")

    out_path = EVAL / f"ie_set_matrix_{args.tag}.md"
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {out_path}  ({len(out)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

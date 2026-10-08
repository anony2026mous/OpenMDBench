"""Small-scale five-arm verification: is the experiment METHOD sound?

This is NOT the baseline.  It answers a narrower set of questions, cheaply, so that a
method problem is found before any full sweep is paid for:

  1. does every arm actually run and produce a VALID scored row (ticks advanced, a
     terminal outcome, not aborted) through the one shared scorecard;
  2. are the arms comparable -- same scenario set, same seed set, same speed
     convention, same scorecard, RL sampled stochastically;
  3. do the health metrics exist per arm (plan calls, parse failures, fallbacks,
     goal adherence for the fifth arm, fire counts) so a degenerate arm is visible
     rather than merely scoring low;
  4. is the spread of a repeat within the arm smaller than the difference we intend
     to interpret -- the hybrid arm measured sd 0.0295 over repeats on IE-01, so a
     gap below that is not interpretable.

Usage:
    python _w1_verify_five_arms.py [--scenarios IE-01-SINGLE-TARGET ...]
        [--seed 7] [--rl-theta PATH] [--arm5-theta PATH] [--jobs 2]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"
RL = RUNS / "rl"
DEFAULT_SCENARIOS = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT"]


def load(planner: str, scenario: str, tag: str, seed: int) -> dict | None:
    suffix = "" if seed == 7 else f"_s{seed}"
    path = RUNS / f"ie_{planner.replace('-', '')}_{scenario.lower()}_{tag}{suffix}.json"
    if not path.is_file():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    card = report.get("strategy_scorecard") or {}
    terminal = card.get("terminal") or {}
    defender = report.get("defender") or {}
    executor = (defender.get("executor") or {}) if isinstance(defender, dict) else {}
    planner_block = (defender.get("planner") or {}) if isinstance(defender, dict) else {}
    ticks = int(report.get("ticks_run") or 0)
    outcome = terminal.get("outcome")
    return {
        "file": path.name,
        "score": card.get("defender_score"),
        "layers": card.get("layers") or {},
        "outcome": outcome,
        "ticks": ticks,
        "consistent": terminal.get("consistent_with_evidence"),
        "aborted": report.get("aborted"),
        "valid": (ticks > 0 and outcome not in (None, "undecided")
                  and not report.get("aborted")),
        "fires_blue": report.get("total_fires_defender"),
        "fires_red": report.get("total_fires_intruder"),
        "plan_calls": planner_block.get("plan_calls"),
        "parse_failures": planner_block.get("parse_failures"),
        "fallback_count": planner_block.get("fallback_count"),
        "executor_fires": executor.get("fires"),
        "adherence": executor.get("adherence"),
        # 速度约定的来源：执行器臂写在 executor 下，纯 RL 臂写在 planner 下
        "speed_source": (executor.get("speed_source")
                         or planner_block.get("speed_source")),
        "speed_provenance": (executor.get("speed_source_provenance")
                             or planner_block.get("speed_source_provenance")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", nargs="*", default=DEFAULT_SCENARIOS)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--tag", default="v5")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--rl-theta", default=str(RL / "theta_rl_legacy2.npz"))
    parser.add_argument("--arm5-theta", default=str(RL / "theta_arm5_v2.npz"))
    parser.add_argument("--rl-speed-source", default="legacy_tags",
                        choices=("catalog", "legacy_tags"),
                        help="RL 臂速度约定，**必须显式给**（对照口径 = legacy_tags）。"
                             "不给就是让默认值去猜，而猜错是静默的（见设计文档 §14.18）。")
    parser.add_argument("--decision-interval", type=int, default=5,
                        help="RL 动作保持时长，必须等于训练值 5。")
    parser.add_argument("--skip-run", action="store_true",
                        help="only read existing reports, do not launch new runs")
    parser.add_argument("--tags", nargs="*", default=None,
                        help="逐臂 tag 覆盖，形如 rule=p18 llm=v5 rl=rlb2 "
                             "llm-rl=v7 rule-rl=rexr2。不给则沿用旧规则："
                             "llm/pure-llm→v5，rule→p18，其余→--tag。"
                             "各臂的文件名 tag 各不相同是常态（不同批次不同 tag），"
                             "写死一个 --tag 会让核验把'没找到文件'报成失败。")
    args = parser.parse_args()

    tag_map: dict[str, str] = {}
    for item in (args.tags or []):
        if "=" in item:
            planner, value = item.split("=", 1)
            tag_map[planner] = value

    # (planner, tag, extra argv, needs theta)
    rl_flags = ["--rl-stochastic", "--rl-speed-source", args.rl_speed_source,
                "--decision-interval", str(int(args.decision_interval))]
    arms = [
        ("rule", tag_map.get("rule", "p18"), [], None),
        ("llm", tag_map.get("llm", "v5"), [], None),
        ("pure-llm", tag_map.get("pure-llm", "v5"), [], None),
        ("rl", tag_map.get("rl", args.tag), rl_flags, args.rl_theta),
        ("llm-rl", tag_map.get("llm-rl", args.tag), rl_flags, args.arm5_theta),
        ("rule-rl", tag_map.get("rule-rl", args.tag), rl_flags, args.arm5_theta),
    ]

    failures: list[str] = []
    if not args.skip_run:
        for planner, tag, extra, theta in arms:
            if theta and not Path(theta).is_file():
                print(f"!! {planner}: checkpoint missing -> {theta}")
                failures.append(f"{planner}: no checkpoint")
                continue
            command = [sys.executable, "-u", str(EVAL / "_w1_ie_sweep.py"),
                       "--planner", planner, "--tag", tag,
                       "--seed", str(args.seed), "--jobs", str(args.jobs),
                       "--scenarios", *args.scenarios]
            if theta:
                command += ["--rl-theta", str(theta)]
            command += extra
            print(f"== running {planner} …", flush=True)
            completed = subprocess.run(command, capture_output=True, text=True,
                                       cwd=str(EVAL), env=dict(os.environ),
                                       timeout=14400)
            tail = (completed.stdout or "").strip().splitlines()[-4:]
            for line in tail:
                print("   " + line.strip())
            if completed.returncode != 0:
                failures.append(f"{planner}: sweep exit {completed.returncode}")

    # ---- validity + comparability table ---------------------------------
    print()
    header = (f"{'scenario':<26}{'arm':<10}{'score':>8}{'outcome':>18}{'ticks':>7}"
              f"{'fires':>7}{'plan':>6}{'fall':>5}  adher  valid")
    print(header)
    print("-" * len(header))
    for scenario in args.scenarios:
        valid_by_arm: dict[str, dict] = {}
        for planner, tag, _extra, _theta in arms:
            row = load(planner, scenario, tag, args.seed)
            if row is None:
                print(f"{scenario:<26}{planner:<10}{'no-file':>8}")
                failures.append(f"{scenario}/{planner}: no report")
                continue
            if row["valid"]:
                valid_by_arm[planner] = row
            adher = row.get("adherence") or {}
            adher_txt = ("n/a" if adher.get("on_assigned_ratio") is None
                         else f"{adher['on_assigned_ratio']:.2f}")
            score = row["score"]
            cells = [
                f"{score:.4f}" if isinstance(score, float) else "n/a",
                str(row["outcome"]),
                str(row["ticks"]),
                str(row["fires_blue"]) if row["fires_blue"] is not None else "-",
                str(row["plan_calls"]) if row["plan_calls"] is not None else "-",
                str(row["fallback_count"]) if row["fallback_count"] is not None else "-",
                adher_txt,
                "ok" if row["valid"] else "INVALID",
            ]
            print(f"{scenario:<26}{planner:<10}{cells[0]:>8}{cells[1]:>18}"
                  f"{cells[2]:>7}{cells[3]:>7}{cells[4]:>6}{cells[5]:>5}"
                  f"  {cells[6]:<6} {cells[7]}")
            # 速度约定必须是**钉住**的，不能是默认值猜的：`theta_rl_legacy2`
            # 就是被这个静默翻转毁掉了一整批读数（见设计文档 §14.18）。
            if planner in ("rl", "llm-rl", "rule-rl"):
                origin = row.get("speed_provenance")
                if origin not in ("argument", "checkpoint_meta"):
                    failures.append(
                        f"{scenario}/{planner}: 速度约定 provenance={origin!r} "
                        f"（值={row.get('speed_source')!r}）—— 必须显式钉住")
            if not row["valid"]:
                failures.append(
                    f"{scenario}/{planner}: invalid (ticks={row['ticks']} "
                    f"outcome={row['outcome']} aborted={str(row['aborted'])[:60]})")
        # spread inside an arm vs between arms
        if len(valid_by_arm) >= 2:
            scores = {k: v["score"] for k, v in valid_by_arm.items()
                      if isinstance(v["score"], float)}
            if len(scores) >= 2:
                spread = max(scores.values()) - min(scores.values())
                print(f"{'':<26}between-arm spread = {spread:.4f}"
                      f"   (hybrid repeat sd measured 0.0295 -> gaps below that are "
                      f"not interpretable)")

    print()
    if failures:
        print(f"VERIFICATION FAILED ({len(failures)} issue(s)):")
        for item in failures:
            print("  -", item)
        return 1
    print("VERIFICATION PASSED: all arms produced valid, comparable rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

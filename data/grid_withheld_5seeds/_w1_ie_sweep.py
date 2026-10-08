"""Batch runner for the IE set: one planner across several scenarios.

Each scenario runs in its own ``run_episode.py`` subprocess so MMG workers and
session state never leak between episodes.  ``--jobs`` runs several scenarios
concurrently (safe: sessions are isolated; the deterministic result of a run does
not depend on what else is on the machine).

Usage:
    python _w1_ie_sweep.py --planner rule [--jobs 3] [--tag f1]
    python _w1_ie_sweep.py --planner rule --scenarios IE-01-SINGLE-TARGET
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import subprocess
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
RUNS = EVAL / "_w1_runs"

IE_SET = [
    "IE-01-SINGLE-TARGET",
    "IE-02-DUAL-THREAT",
    "IE-03-SURFACE-RAID",
    "IE-04-COMBINED-ARMS",
    "IE-05-MULTI-AXIS",
    "IE-06-DECOY-MIXED",
    "IE-07-CROSS-DOMAIN",
    "IE-08-ISLAND-STRIKE",
    "IE-09-STAGGERED-WAVES",
    "IE-10-DUAL-AXIS-PINCER",
    "IE-11-DECOY-SCREEN",
    "IE-12-FOG-ONSET",
    "IE-13-DEEP-STRIKE",
    "IE-14-SATURATION-THREE-WAVE",
]
# 每个场景的 horizon 由 world.duration_ticks 决定；这里留出余量交给引擎自锁终局。
MAX_TICKS = 1800


def run_one(planner: str, scenario: str, tag: str, seed: int,
            rl_theta: str | None = None,
            rl_stochastic: bool = False,
            decision_interval: int | None = None,
            rl_speed_source: str | None = None,
            rl_overkill_release: bool = False,
            wall_limit: int = 5400,
            hard_timeout: int = 7200,
            step_timeout: float = 60.0,
            pure_llm_envelope: str | None = None,
            llm_briefing: str | None = None) -> tuple[str, bool, str]:
    # 输出名带上 seed：多 seed 复算必须各自留档，否则互相覆盖。
    # （引擎把命中判定种子挂在 resolved_hash + session_id 上，
    #   而 session_id 由 seed 推出 —— 所以换 seed 就是换一整条抽签流。）
    suffix = "" if seed == 7 else f"_s{seed}"
    output = RUNS / f"ie_{planner.replace('-', '')}_{scenario.lower()}_{tag}{suffix}.json"
    log = RUNS / "logs" / f"{output.stem}.jsonl"
    command = [
        sys.executable, "-u", str(EVAL / "run_episode.py"),
        "--scenario", scenario,
        "--planner", planner,
        "--seed", str(seed),
        "--max-ticks", str(MAX_TICKS),
        "--report-every", "400",
        "--log", str(log),
        "--checkpoint-dir", str(RUNS / "checkpoints"),
        "--output", str(output),
    ]
    if planner in ("llm", "pure-llm", "llm-rl"):
        # llm-rl plans with the SAME LLM on the same cadence as the hybrid arm; only
        # its executor differs, so it needs the same planning knobs.
        #
        # 墙钟上限必须留足余量：MD-AD-006 满局（1799 tick）在无争用时约 85 分钟，
        # 而这里过去硬编码 5400s（90 分钟）——只有 6% 余量。一旦并发把每 tick 的
        # LLM 等待拉长，整局会在跑到终局前被 wall_limit 掐掉，白烧一个半小时。
        command += ["--plan-interval", "10", "--wall-limit", str(int(wall_limit))]
        # 单 tick 看门狗也必须放宽：LLM 臂的每次规划调用（默认 10 tick 一次）
        # 会把那一个 tick 的墙钟抬到"一次调用延迟"的量级。空闲时 ≈19 s，
        # 6~9 路并发时 25~35 s，网络错误重试还会翻倍。
        # 实测踩到：MD-AD-006 在 9 路并发下 tick 0 用了 60.7 s > 默认 60 s，
        # 整局被判 `step_timeout` 中止（得分 0.35 的垃圾数据）。这不是语义问题，
        # 纯粹是看门狗阈值没跟着并发量走。
        command += ["--step-timeout", str(float(step_timeout))]
    if planner == "pure-llm" and pure_llm_envelope:
        # 速度包线对等性对照：其它臂走 executor 表（IE 集 43/8），
        # 历史 pure-llm 硬编码 45/10 —— 水面 +25% 会让它追得上 10 m/s 的自爆船。
        command += ["--pure-llm-envelope", str(pure_llm_envelope)]
    if planner in ("llm", "pure-llm", "llm-rl") and llm_briefing:
        # 作战简报口径：withheld=不给未来真值（公平），declared=历史口径。
        command += ["--llm-briefing", str(llm_briefing)]
    if planner in ("rl", "llm-rl", "rule-rl") and decision_interval is not None:
        # 纯 RL 臂没有 LLM，它的"决策间隔"就是策略的动作保持时长，
        # 必须等于**训练时**的保持时长（`--decision-interval`，默认 5）。
        # run_episode 的 `rl` 分支过去读的是 `--plan-interval`（LLM 规划节奏，
        # 默认 10），于是所有纯 RL 读数其实是在**训练值 2 倍**的保持时长下评测的
        # —— 典型的 train/eval 错配。这里显式把它接到正确旋钮上。
        # rule-rl / llm-rl 的 RL 执行层本来就读 `--decision-interval`。
        command += ["--decision-interval", str(int(decision_interval))]
    if planner in ("rl", "llm-rl", "rule-rl"):
        # Same scoring path as the other arms: run_episode drives the policy over the
        # session the harness owns and steps.  For llm-rl that policy is the executor
        # beneath the LLM planner rather than the whole controller.
        if not rl_theta:
            return scenario, False, f"--planner {planner} 需要 --rl-theta <theta.npz>"
        theta_path = Path(rl_theta).expanduser().resolve()
        if not theta_path.is_file():
            return scenario, False, f"checkpoint not found: {theta_path}"
        command += ["--rl-theta", str(theta_path)]
        if rl_stochastic:
            # Taking each head's marginal argmax is NOT the mode of the joint
            # action: for a factored multi-unit policy it collapses every unit onto
            # the same choice.  Measured on one checkpoint, one seed, one scenario:
            # deterministic 0.1342 (facility lost at t161, 6 shots) vs stochastic
            # 0.6613 (held to t213, 12 shots) -- a 5x gap from the sampling mode
            # alone.  The policy IS a distribution, so its expected score is what
            # the comparison should use.
            command += ["--rl-stochastic"]
        if rl_speed_source:
            # Must be pinned to the checkpoint's TRAINING convention.  Leaving it to
            # a default is how a whole batch became invalid: `theta_rl_legacy2` was
            # trained with legacy_tags while `rl_agent.py` defaults to catalog, so
            # the arm was evaluated with an 80/10 speed table it had never seen.
            command += ["--rl-speed-source", str(rl_speed_source)]
        if rl_overkill_release:
            # 诊断开关：只用于证明"一轮齐射失败后目标被永久封禁"这一缺陷的因果
            # （IE-03 有 14 枚面面导弹却只允许打 6 发）。默认不开，以保持与
            # 冻结规则执行器同语义、消融对等。
            command += ["--rl-overkill-release"]
    completed = subprocess.run(command, capture_output=True, text=True,
                               cwd=str(ROOT), env=dict(os.environ),
                               timeout=int(hard_timeout))
    if completed.returncode != 0 or not output.exists():
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()[-6:]
        return scenario, False, " | ".join(tail) or f"exit={completed.returncode}"
    report = json.loads(output.read_text(encoding="utf-8"))
    scorecard = report.get("strategy_scorecard") or {}
    overall = scorecard.get("defender_score")
    outcome = (report.get("layered_metrics") or {}).get("outcome")
    # ---- 成功判据必须严于"文件存在" --------------------------------------
    # `run_episode` 在异常/中止时**照样写出报告**（这是有意的：保留现场）。于是
    # "文件存在"并不代表"跑成了"。实测踩到过：LLM 端点连不上时 episode 在
    # tick 0 就中止，报告里 ticks_run=0、terminal.outcome=null、aborted=异常文本，
    # 记分卡仍给出一个 0.3889 的分数 —— 扫局脚本却打印 [ok]，三臂矩阵会被
    # 静默填进一行垃圾数据。这里按"真的推进过 + 有终局结论"判定成功。
    ticks = int(report.get("ticks_run") or 0)
    terminal = scorecard.get("terminal") or {}
    if ticks <= 0 or terminal.get("outcome") in (None, "undecided") or report.get("aborted"):
        reason = report.get("aborted") or report.get("error") or "no terminal outcome"
        return scenario, False, f"aborted/无效局: ticks={ticks} {str(reason)[:220]}"
    return (scenario, True,
            f"ticks={report.get('ticks_run')} score={overall} {outcome} "
            f"fires={report.get('total_fires')} -> {output.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--planner", required=True,
                        choices=("rule", "llm", "pure-llm", "rl", "llm-rl", "rule-rl"))
    parser.add_argument("--rl-theta", default=None,
                        help="--planner rl 用的策略权重（theta_<tag>.npz）。")
    parser.add_argument("--rl-stochastic", action="store_true",
                        help="RL 臂按分布采样而非取众数。**对照应该用这个**："
                             "逐头取 argmax 不是联合动作的众数，会把每个单元压成同一个选择。")
    parser.add_argument("--decision-interval", type=int, default=None,
                        help="仅 llm-rl：RL 执行层的决策间隔（默认用其训练值 5）。"
                             "设 1 可把控制带宽对齐到规则执行器（后者每 tick 重解），"
                             "用于量化'带宽差异'单独贡献了多少分差。")
    parser.add_argument("--rl-speed-source", default=None,
                        choices=("catalog", "legacy_tags"),
                        help="RL 臂的速度包线约定，**必须等于 checkpoint 训练时用的那个**。"
                             "legacy_tags=规则执行器的 40/8 表（消融对照用）；"
                             "catalog=平台真实上限 80/10。留空则由 run_episode 推断"
                             "（会记 provenance，推断来的值不可信）。")
    parser.add_argument("--rl-overkill-release", action="store_true",
                        help="仅 RL 执行层：齐射被评估为失败时归还超杀计数（诊断开关）。")
    parser.add_argument("--pure-llm-envelope", default="executor",
                        choices=("hardcoded", "executor"),
                        help="仅 pure-llm：速度上限来源。**默认 executor**=与其它所有臂"
                             "同表（IE 集 43/8）。hardcoded=历史的 45/10，仅供复现"
                             "2026-02-05 之前的旧读数。自爆船 10 m/s，8 m/s 的我方无人船"
                             "追不上、10 m/s 的追得上。")
    parser.add_argument("--scenarios", nargs="*", default=None)
    parser.add_argument("--llm-briefing", default="withheld",
                        choices=("withheld", "declared"),
                        help="仅 LLM 臂：作战简报口径。**withheld（默认）**=不给未来"
                             "波次时刻/方位/意图（公平口径）；"
                             "declared=历史口径，含未来真值（仅用于复现旧读数）。")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--tag", default="f1")
    parser.add_argument("--seed", type=int, default=7,
                        help="会话种子。引擎的命中判定由 resolved_hash+session_id "
                             "推出，换 seed 即换整条抽签流；>1 个 seed 用于给出"
                             "分数噪声带，避免把重抽当成设计改动。")
    parser.add_argument("--wall-limit", type=int, default=5400,
                        help="单局墙钟上限（秒），透传给 run_episode。MD-AD-006 满局"
                             "在无争用时已需 ~5100s，测长局时务必抬高。")
    parser.add_argument("--episode-timeout", type=int, default=7200,
                        help="扫局侧对单个 episode 子进程的硬超时（秒），必须大于"
                             "--wall-limit，否则子进程还没到自己的墙钟就被杀掉。")
    parser.add_argument("--step-timeout", type=float, default=60.0,
                        help="单 tick 墙钟看门狗（秒），透传给 run_episode。LLM 臂在"
                             "多路并发下单次规划调用可达 25~35 s，重试再翻倍；"
                             "默认 60 s 会在并发时把整局误判为 step_timeout 中止。"
                             "测 LLM 臂建议 ≥180。")
    args = parser.parse_args()

    scenarios = args.scenarios or IE_SET
    RUNS.mkdir(parents=True, exist_ok=True)
    print(f"planner={args.planner} scenarios={len(scenarios)} jobs={args.jobs} "
          f"tag={args.tag} seed={args.seed}", flush=True)

    failures = []
    with futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        pending = {pool.submit(run_one, args.planner, name, args.tag, args.seed,
                               args.rl_theta, args.rl_stochastic,
                               args.decision_interval,
                               args.rl_speed_source,
                               args.rl_overkill_release,
                               args.wall_limit,
                               args.episode_timeout,
                               args.step_timeout,
                               args.pure_llm_envelope,
                               args.llm_briefing): name
                   for name in scenarios}
        for future in futures.as_completed(pending):
            scenario, ok, detail = future.result()
            mark = "ok  " if ok else "FAIL"
            print(f"  [{mark}] {scenario:<26} {detail}", flush=True)
            if not ok:
                failures.append(scenario)

    print(f"\n  {len(scenarios) - len(failures)}/{len(scenarios)} runs ok")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

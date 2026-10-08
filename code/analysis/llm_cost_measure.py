"""千问规划调用成本实测：在真实对局中逐次记录 LLM 耗时与 reasoning 字段占比。

跑到引擎 kill bug 崩溃为止（或 max_ticks），统计：
- 每次规划调用：延迟、提示词 token、完成 token、内容字符数、reasoning 字段字符数
- reasoning 字段的 token/时间占比（按"字符占比 × 完成 token"估算，字段与 JSON 同为 ASCII）
- 折算到一整局（180 次调用）reasoning 字段贡献多少时间

用法（Linux、仓库根目录）：
    PYTHONPATH=$PWD MPLCONFIGDIR=/tmp/openmdbench-mpl .venv/bin/python \
      ../eval_w1/llm_cost_measure.py --max-ticks 400 --plan-interval 10
"""

from __future__ import annotations

import argparse
import json
import re
import time

import requests

from openmdbench.sessions.formal_v2 import create_formal_session_v2

from attack_driver import AttackProfileDriverV2, load_attack_profile_data
from llm_planner import LLMPlannerV2
from rule_planner import RulePlannerConfigV2, RulePlannerV2
from v2_agent import AgentV2
from llm_client_hifi import LLMClient
from v2_executor import ExecutorConfigV2, WeaponPolicyV2


class InstrumentedLLM(LLMClient):
    """继承流式 LLMClient，逐次记录 usage 与 reasoning 字段长度。"""

    def __init__(self, base_url: str, model: str, max_tokens: int = 2048):
        super().__init__(base_url=base_url, model=model, max_tokens=max_tokens,
                         enable_thinking=False)
        self.calls: list[dict] = []

    def chat(self, system_prompt: str, user_message: str,
             max_tokens: int = None, temperature: float = 0.1) -> str:
        started = time.perf_counter()
        content = super().chat(system_prompt, user_message,
                               max_tokens=max_tokens, temperature=temperature)
        latency = time.perf_counter() - started
        usage = self._last_usage
        reasoning_chars = _reasoning_chars(content)
        self.calls.append({
            "latency_s": round(latency, 2),
            "prompt_tokens": int(usage.get("prompt_tokens", 0)),
            "completion_tokens": int(usage.get("completion_tokens", 0)),
            "content_chars": len(content),
            "reasoning_chars": reasoning_chars,
        })
        return content

    def get_stats(self) -> dict:
        return {"instrumented_calls": len(self.calls)}


def _reasoning_chars(content: str) -> int:
    match = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"', content)
    return len(match.group(1)) if match else 0


def _build_defender_llm(profile_data, llm, plan_interval: int) -> AgentV2:
    defence = profile_data["defence"]
    faction_id = str(defence["faction_id"])
    policies = tuple(
        WeaponPolicyV2(
            selector_tags=tuple(str(t) for t in p.get("selector_tags", ())),
            weapon_ref=str(p["weapon_ref"]),
            minimum_range_m=float(p["minimum_range_m"]),
            maximum_range_m=float(p["maximum_range_m"]),
            cooldown_ticks=int(p["cooldown_ticks"]),
        )
        for p in defence.get("weapon_policies", ())
    )
    executor_config = ExecutorConfigV2(
        faction_id=faction_id,
        weapon_policies=policies,
        speed_by_tag={"interceptor": float(defence.get("intercept_speed_mps", 40.0)),
                      "picket": 8.0},
    )
    planner_config = RulePlannerConfigV2(
        confidence_min=float(defence.get("contact_confidence", 0.55)),
        contact_max_age_ticks=int(defence.get("maximum_contact_age_ticks", 10)),
    )
    planner = LLMPlannerV2(
        planner_config, llm=llm, fallback_planner=RulePlannerV2(planner_config),
        max_tokens=2048,
    )
    return AgentV2(planner=planner, executor_config=executor_config,
                   faction_id=faction_id, plan_interval=plan_interval,
                   name="defender.llm")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="MD-AD-002-EASY")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-ticks", type=int, default=400)
    parser.add_argument("--plan-interval", type=int, default=10)
    parser.add_argument("--base-url", default="http://172.18.116.170:8000/v1")
    parser.add_argument("--model", default="Qwen3.8-27B")
    args = parser.parse_args()

    profile = load_attack_profile_data(args.scenario)
    llm = InstrumentedLLM(args.base_url, args.model)
    session = create_formal_session_v2(
        args.scenario, session_id="eval.cost.measure", seed=args.seed
    )
    attack = AttackProfileDriverV2(args.scenario, seed=args.seed)
    defender = _build_defender_llm(profile, llm, args.plan_interval)
    session.load().start()
    stop_reason = f"max_ticks={args.max_ticks}"
    try:
        for _ in range(args.max_ticks):
            tick = session.world_view.tick
            attack(session)
            defender(session)
            try:
                session.step(operation_id=f"cost.tick.{tick}", expected_tick=tick)
            except ValueError as error:
                stop_reason = f"kill-bug at tick {tick}: {str(error)[:60]}"
                break
    finally:
        try:
            session.stop()
        except Exception:  # noqa: BLE001 failed-op 状态下 stop 可能失败
            pass
        session.close()

    calls = llm.calls
    print(f"== 千问规划成本实测（{len(calls)} 次规划，止于 {stop_reason}）==")
    for i, c in enumerate(calls):
        share = (c["reasoning_chars"] / c["content_chars"] * 100.0
                 if c["content_chars"] else 0.0)
        print(f"[call {i + 1:>2}] 延迟={c['latency_s']:>6.1f}s "
              f"提示={c['prompt_tokens']:>4}tok 完成={c['completion_tokens']:>4}tok "
              f"内容={c['content_chars']:>5}字符 reasoning={c['reasoning_chars']:>4}字符"
              f"({share:>4.1f}%)")
    if not calls:
        print("没有任何 LLM 调用（可能引擎未到首次规划即崩溃）")
        return 1

    total_latency = sum(c["latency_s"] for c in calls)
    total_completion = sum(c["completion_tokens"] for c in calls)
    total_content = sum(c["content_chars"] for c in calls)
    total_reasoning = sum(c["reasoning_chars"] for c in calls)
    char_share = total_reasoning / total_content * 100.0 if total_content else 0.0
    est_reasoning_tokens = total_completion * (total_reasoning / total_content) \
        if total_content else 0.0
    # 生成速度 = 完成token/（总延迟 - 排队与预填充），用整段延迟作为分母的
    # 粗估会低估速度；这里按"内容字符→token 比例"直接估 reasoning 的 token，
    # 再按本次实测的有效吞吐折算时间。
    tok_per_s = total_completion / total_latency if total_latency > 0 else 0.0
    reasoning_time = est_reasoning_tokens / tok_per_s if tok_per_s > 0 else 0.0
    avg_latency = total_latency / len(calls)
    avg_prompt = sum(c["prompt_tokens"] for c in calls) / len(calls)

    print("== 汇总 ==")
    print(f"规划次数: {len(calls)}  总 LLM 耗时: {total_latency:.1f}s "
          f"(平均 {avg_latency:.1f}s/次)")
    print(f"提示词: 平均 {avg_prompt:.0f} tok/次")
    print(f"完成 token 合计: {total_completion}")
    print(f"reasoning 字段: 字符占比 {char_share:.1f}% → 估算 token "
          f"~{est_reasoning_tokens:.0f} (占完成 {est_reasoning_tokens / total_completion * 100:.1f}%)")
    print(f"reasoning 折算生成时间: 约 {reasoning_time:.1f}s "
          f"(占 LLM 总耗时 {reasoning_time / total_latency * 100:.1f}%)")
    for calls_per_episode in (90, 180, 360):
        episode_cost = reasoning_time / len(calls) * calls_per_episode
        print(f"一整局折算({calls_per_episode} 次规划): reasoning 字段贡献 "
              f"~{episode_cost / 60:.1f} 分钟")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

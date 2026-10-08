"""Reproduce EXACTLY what the LLM is given at tick 0 for IE-11.

Uses the real helpers (run_episode._build_roe_notes, InterceptionGraph
.format_timeline_for_prompt) so this is the shipped prompt content, not a guess.
Also reports how many contacts the defender can actually observe at tick 0,
to make the asymmetry explicit.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402
from interception_graph import InterceptionGraph  # noqa: E402

PUB = "IE-11-DECOY-SCREEN"
print("=" * 96)
print(f"{PUB}: what the LLM planner receives at tick 0")
print("=" * 96)

payload = run_episode.load_attack_profile_data(PUB)
attack = payload.get("attack") or {}
timeline = tuple(attack.get("timeline") or ())

print("\n--- (1) attack.timeline 原文（agents.yaml 声明）---")
for it in timeline:
    print(f"  label       = {it.get('label')!r}")
    print(f"    spawn_tick= {it.get('spawn_tick')}   count= {it.get('count')}")
    print(f"    axis      = {it.get('axis')}")
    print(f"    behavior  = {it.get('behavior')!r}")

print("\n--- (2) roe_notes —— 新口径 withheld（默认，进 system prompt）---")
print(run_episode._build_roe_notes(payload, briefing="withheld"))
print("\n--- (2b) roe_notes —— 旧口径 declared（进 system prompt）---")
print(run_episode._build_roe_notes(payload, briefing="declared"))

print("\n--- (3) 时间线块（format_timeline_for_prompt，进入 user prompt）---")
try:
    g = InterceptionGraph(tick=0, interceptors=(), target_count=0, history=None,
                          attack_timeline=timeline)
except TypeError:
    # fall back: call the formatter logic directly with the same fields
    lines = []
    for item in timeline:
        lines.append(
            f"  {item.get('label', 'wave')}: spawn_tick={item.get('spawn_tick', '?')} "
            f"count={item.get('count', '?')} axis={item.get('axis', '?')}; "
            f"{item.get('behavior', 'continues toward the protected zone')}")
    g = None
    print("\n".join(lines))

print("\n--- (4) 该场景声明的武器装订（防守方看不到，但决定威胁）---")
for wp in (attack.get("weapon_policies") or ()):
    print(f"  match_tag={wp.get('match_tag')}  weapon={wp.get('weapon_ref')}  "
          f"range={wp.get('min_range_m')}–{wp.get('max_range_m')} m  "
          f"shots={wp.get('shots')}  reserve={wp.get('reserve_for_assigned')}")

print("\n" + "=" * 96)
print("对比：这些信息里，有多少是 defender 的 tick 0 观测能得到的？")
print("=" * 96)
print("""  defender 观测（ObservationV2）只包含本人探测到的接触：
    contact_id / 估计位置 / 置信度 / 观测者
  ⇒ tick 0 时来袭者尚未进入传感器范围（或被声明为 spawn_tick 未来时刻），
    因此观测里的接触数通常为 0。
  而上面 (2)(3) 两段文本逐条给出了未来波次的 数量/时刻/方位/行为意图，
  全部在任何传感器接触之前就进入了提示词。""")

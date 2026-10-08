"""End-to-end check that the prompts now carry the REAL envelope.

Instantiates PureLLMAgentV2 through the harness path and greps its actual
system prompt for:
  * the declared speed range (must equal the scenario envelope, not 0-45)
  * the few-shot example speed (must equal the envelope cap, not 40)
  * absence of the old constants
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402
import pure_llm_agent  # noqa: E402

captured = {}


class StubLLM:
    def chat(self, *a, **k):
        return '{"actions": {}}'


for pub in ("IE-01-SINGLE-TARGET", "IE-08-ISLAND-STRIKE", "IE-11-DECOY-SCREEN"):
    payload = run_episode.load_attack_profile_data(pub)
    parser = run_episode.build_parser()
    args = parser.parse_args(["--scenario", pub, "--seed", "7",
                              "--planner", "pure-llm", "--max-ticks", "5"])
    real = pure_llm_agent.PureLLMAgentV2
    holder = {}

    class Spy(real):  # type: ignore[misc,valid-type]
        def __init__(self, **kw):
            holder.update(kw)
            super().__init__(**kw)

    pure_llm_agent.PureLLMAgentV2 = Spy
    try:
        agent = run_episode._build_defender(payload, args)
    finally:
        pure_llm_agent.PureLLMAgentV2 = real

    env = dict(holder.get("speed_max_by_tag") or {})
    sysp = agent._system_prompt
    ex = re.findall(r'"speed_mps":\s*(\d+)', sysp)
    rng = re.findall(r"speed_mps\":\s*<([^>]+)>", sysp)

    print("=" * 78)
    print(pub)
    print("=" * 78)
    print(f"  envelope passed in        : {env}")
    print(f"  prompt speed bound        : {rng}")
    print(f"  few-shot example speed(s) : {sorted(set(ex))}")
    print(f"  still says 0-45?          : {'0-45' in sysp}")
    print(f"  examples all <= cap?      : "
          f"{all(int(v) <= max(env.values()) for v in ex) if ex else 'n/a'}")
    print()

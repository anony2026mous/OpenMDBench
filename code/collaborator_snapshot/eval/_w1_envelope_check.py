"""Prove the pure-llm envelope now equals the executor table the other 5 arms use.

Uses the REAL argparse parser (not a hand-written Namespace) and intercepts the
PureLLMAgentV2 constructor, so the check exercises the production code path and
costs no LLM calls.
"""
from __future__ import annotations

import sys

EVAL = r"C:\Code\source-code\openmd\code\eval"
sys.path.insert(0, EVAL)

import run_episode  # noqa: E402
import pure_llm_agent  # noqa: E402

captured: dict = {}


class FakeAgent:
    def __init__(self, **kw):
        captured.update(kw)


def envelope_for(extra_argv):
    """Build the defender with the given CLI flags and return pure-llm's envelope."""
    captured.clear()
    parser = run_episode.build_parser()
    argv = ["--scenario", "IE-01-SINGLE-TARGET", "--seed", "7",
            "--planner", "pure-llm", "--max-ticks", "5"] + list(extra_argv)
    args = parser.parse_args(argv)
    payload = run_episode.load_attack_profile_data("IE-01-SINGLE-TARGET")
    real = pure_llm_agent.PureLLMAgentV2
    pure_llm_agent.PureLLMAgentV2 = FakeAgent
    try:
        run_episode._build_defender(payload, args)
    finally:
        pure_llm_agent.PureLLMAgentV2 = real
    return dict(captured.get("speed_max_by_tag") or {}), args


# what the other five arms actually use: read it off the same code path (rule arm)
def executor_table():
    parser = run_episode.build_parser()
    args = parser.parse_args(["--scenario", "IE-01-SINGLE-TARGET", "--seed", "7",
                              "--planner", "rule", "--max-ticks", "5"])
    payload = run_episode.load_attack_profile_data("IE-01-SINGLE-TARGET")
    seen = {}
    import v2_executor
    real = v2_executor.ExecutorConfigV2
    import run_episode as re_mod
    orig = re_mod.ExecutorConfigV2
    class Spy(real):  # type: ignore[misc,valid-type]
        def __init__(self, **kw):
            seen.update(kw)
            super().__init__(**kw)
    re_mod.ExecutorConfigV2 = Spy
    v2_executor.ExecutorConfigV2 = Spy
    try:
        agent = run_episode._build_defender(payload, args)
    finally:
        re_mod.ExecutorConfigV2 = orig
        v2_executor.ExecutorConfigV2 = real
    return dict(seen.get("speed_by_tag") or {})


table = executor_table()
print("other 5 arms use (IE-01, from the rule arm's ExecutorConfigV2):")
print("   ", table)
print()

blank = envelope_for([])
print("pure-llm with NO flag (i.e. the new default):")
print("   ", blank[0])
print("    identical to the other arms' table:",
      all(abs(blank[0].get(k, -1) - table.get(k, -2)) < 1e-9 for k in blank[0]) if table else "n/a")
print()

exec_ = envelope_for(["--pure-llm-envelope", "executor"])
print("pure-llm --pure-llm-envelope executor:")
print("   ", exec_[0])
print()

hard = envelope_for(["--pure-llm-envelope", "hardcoded"])
print("pure-llm --pure-llm-envelope hardcoded (legacy, for reproducing old runs):")
print("   ", hard[0])
print()

print("default resolves to:", "executor" if blank[0] == exec_[0] else "hardcoded")

"""Decisive leak test: build the ACTUAL prompt and grep it for enemy-plan content.

Instrumenting the planner is the only way to be sure. We substitute the LLM client
with a stub that captures the exact system+user prompt that would be sent, then
search for scenario-declared facts that the other arms cannot obtain:
  spawn tick numbers, wave axes, wave counts, labels, and behavior prose.
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402
import llm_planner  # noqa: E402
from interception_graph import InterceptionGraph  # noqa: E402

PUB = "IE-11-DECOY-SCREEN"

# words that only exist in the scenario declaration, never in an observation
SENSITIVE = [
    "decoy screen", "real air package", "surface element",
    "spawn_tick", "south-east", "north-east", "15-19 km", "7-9 km",
    "turn away at tick 150", "drawn attention", "harbour-mouth",
    "declared DECOYS", "NON-THREAT", "declared briefing",
]


class CaptureLLM:
    def __init__(self):
        self.last = None
        self.calls = 0

    def chat(self, system, user, **kw):
        self.calls += 1
        self.last = (system, user)
        # return a syntactically valid empty plan
        return '{"goal_commands": [], "reasoning": "capture"}'


def build_prompt(briefing: str):
    cap = CaptureLLM()
    payload = run_episode.load_attack_profile_data(PUB)
    import argparse
    parser = run_episode.build_parser()
    args = parser.parse_args(["--scenario", PUB, "--seed", "7", "--planner", "llm",
                              "--max-ticks", "5", "--llm-briefing", briefing])
    # replicate the prompt_context that _build_defender would construct
    ctx = {
        "objective": [0.0, 0.0],
        "weapon_range": 8000.0,
        "roe_notes": run_episode._build_roe_notes(payload, briefing=briefing),
        "briefing_declared": briefing == "declared",
        "default_fire_policy": "assess",
        "intruder_speed_mps": 43.0,
    }
    gb = InterceptionGraph.__new__(InterceptionGraph)   # minimal stand-in
    planner = llm_planner.LLMPlannerV2(
        run_episode.RulePlannerConfigV2(), llm=cap,
        fallback_planner=run_episode.RulePlannerV2(run_episode.RulePlannerConfigV2()),
        prompt_context=ctx, graph_builder=None)
    # call the non-graph prompt path (which also embeds roe_notes)
    p = planner._build_prompt.__self__  # noqa: F841  (documentation only)
    planner._build_prompt(payload, 0, [], None)
    return cap.last


for mode in ("withheld", "declared"):
    sysp, usr = build_prompt(mode)
    blob = (sysp or "") + "\n" + (usr or "")
    hits = [s for s in SENSITIVE if s.lower() in blob.lower()]
    print("=" * 88)
    print(f"briefing = {mode}   prompt chars: system={len(sysp or '')} user={len(usr or '')}")
    print("=" * 88)
    if hits:
        print(f"  LEAK: {len(hits)} scenario-declared strings present:")
        for h in hits:
            print(f"      {h!r}")
    else:
        print("  clean: no scenario-declared enemy-plan strings in the prompt")
    print()

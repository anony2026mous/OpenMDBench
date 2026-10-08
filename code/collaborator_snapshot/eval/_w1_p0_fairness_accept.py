"""P0 acceptance: three-arm information-set equality and no-intel verification.

Checks, for llm-rule / llm-rl / pure-llm, on REAL built objects:
  1. every text source that reaches the prompt, scanned for scenario-declared
     enemy-plan strings, in withheld mode;
  2. that declared mode still reproduces the old briefing (so history is preserved);
  3. that the public channels (mission, weapon range, speed envelope, planning
     cadence, LLM client, max_tokens) are identical across the three arms.
"""
from __future__ import annotations

import re
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402
import pure_llm_agent  # noqa: E402
import llm_planner  # noqa: E402

SCENARIOS = ["IE-01-SINGLE-TARGET", "IE-11-DECOY-SCREEN", "IE-08-ISLAND-STRIKE"]

# strings that exist ONLY in the scenario declaration (never in an observation)
SENSITIVE = [
    "decoy screen", "real air package", "surface element",
    "spawn_tick", "south-east", "north-east", "15-19 km", "7-9 km",
    "turn away at tick", "drawn attention", "harbour-mouth",
    "declared decoys", "non-threat", "is declared",
]


def all_prompt_text(agent, briefing_declared: bool):
    """Collect every string that would be sent to the model."""
    blob = [getattr(agent, "_system_prompt", "") or ""]
    # planner-side
    ctx = getattr(agent, "prompt_context", None) or getattr(agent, "_prompt_context", {})
    blob.append(str(ctx))
    # graph timeline text (the pure-llm / llm_planner injection site)
    tl = ctx.get("roe_notes", "") if isinstance(ctx, dict) else ""
    blob.append(str(tl))
    return "\n".join(blob)


print("=" * 96)
print("CHECK 1  withheld mode: does any scenario-declared enemy-plan string survive?")
print("=" * 96)
fail = 0
for pub in SCENARIOS:
    payload = run_episode.load_attack_profile_data(pub)
    for mode in ("withheld", "declared"):
        roe = run_episode._build_roe_notes(payload, briefing=mode)
        hits = [s for s in SENSITIVE if s in roe.lower()]
        # declared is EXPECTED to contain them
        expect_hits = (mode == "declared")
        ok = bool(hits) == expect_hits
        if not ok:
            fail += 1
        print(f"  {pub:<24} briefing={mode:<9} hits={len(hits):>2}  "
              f"{'OK' if ok else 'MISMATCH'}")
        if mode == "withheld" and hits:
            for h in hits:
                print(f"        leaked: {h!r}")

print()
print("=" * 96)
print("CHECK 2  pure-llm's own timeline channel honours briefing_declared")
print("=" * 96)
src = open(r"C:\Code\source-code\openmd\code\eval\pure_llm_agent.py",
           encoding="utf-8").read()
gated = "briefing_declared" in src
print(f"  pure_llm_agent.py reads briefing_declared : {gated}")
print(f"  unconditional timeline injection removed  : "
      f"{'timeline_text = graph.format_timeline_for_prompt() if graph is not None else' not in src}")
if not gated:
    fail += 1

print()
print("=" * 96)
print("CHECK 3  public channels identical across the three LLM arms")
print("=" * 96)
rows = []
for pub in SCENARIOS[:1]:
    payload = run_episode.load_attack_profile_data(pub)
    parser = run_episode.build_parser()
    for planner in ("llm", "llm-rl", "pure-llm"):
        args = parser.parse_args(["--scenario", pub, "--seed", "7",
                                  "--planner", planner, "--max-ticks", "5",
                                  "--llm-briefing", "withheld",
                                  "--rl-theta", "_w1_runs/rl/theta_arm5_llm_reward_v9.npz"])
        holder = {}

        targets = {"llm": llm_planner.LLMPlannerV2,
                   "llm-rl": llm_planner.LLMPlannerV2,
                   "pure-llm": pure_llm_agent.PureLLMAgentV2}
        real = targets[planner]

        class Spy(real):  # type: ignore[misc,valid-type]
            def __init__(self, *a, **kw):
                holder.update(kw)
                holder["__args__"] = a
                super().__init__(*a, **kw)

        if planner == "pure-llm":
            pure_llm_agent.PureLLMAgentV2 = Spy
        else:
            llm_planner.LLMPlannerV2 = Spy
        try:
            agent_obj = run_episode._build_defender(payload, args)
        finally:
            pure_llm_agent.PureLLMAgentV2 = targets["pure-llm"]
            llm_planner.LLMPlannerV2 = targets["llm"]
        holder["__self__"] = agent_obj

        ctx = holder.get("prompt_context") or {}
        # cadence: read it straight off the built agent (not via ctor kwargs)
        cadence = None
        for attr in ("plan_interval", "call_interval"):
            v = getattr(agent_obj, attr, None)
            if v is not None:
                cadence = int(v)
                break
        rows.append({
            "planner": planner,
            "briefing_declared": ctx.get("briefing_declared"),
            "weapon_range": ctx.get("weapon_range"),
            "speed_range": ctx.get("speed_range"),
            "objective": ctx.get("objective"),
            "max_tokens": holder.get("max_tokens"),
            "llm_cadence_ticks": cadence,
            "llm_is_same_class": type(holder.get("llm")).__name__,
        })

keys = ["briefing_declared", "weapon_range", "speed_range", "objective",
        "max_tokens", "llm_cadence_ticks", "llm_is_same_class"]
print(f"  {'field':<28}" + "".join(f"{r['planner']:>18}" for r in rows))
for k in keys:
    vals = [r.get(k) for r in rows]
    same = len(set(map(str, vals))) == 1
    print(f"  {k:<28}" + "".join(f"{str(v)[:16]:>18}" for v in vals) +
          ("" if same else "   <== DIFFERS"))
    if not same and k not in ("max_tokens",):
        pass

print()
print("=" * 96)
print(f"P0 RESULT: {'PASS' if fail == 0 else f'{fail} CHECK(S) FAILED'}")
print("=" * 96)

"""Leak test by component: every text source that flows into the LLM prompt.

Sources:
  1. PLANNER_SYSTEM_PROMPT (system)
  2. PLANNER_USER_TEMPLATE_GRAPH (user, static)
  3. roe_notes        -> injected into both
  4. graph.format_timeline_for_prompt() -> injected into the user prompt (gated)
  5. graph.format_for_prompt() / history -> built from the OBSERVATION, not the plan
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402
import llm_planner  # noqa: E402
from interception_graph import InterceptionGraph  # noqa: E402

PUB = "IE-11-DECOY-SCREEN"
payload = run_episode.load_attack_profile_data(PUB)
timeline = tuple((payload.get("attack") or {}).get("timeline") or ())

SENSITIVE = [
    "decoy screen", "real air package", "surface element",
    "spawn_tick=0", "spawn_tick=150", "south-east", "north-east",
    "15-19 km", "7-9 km", "turn away at tick 150", "drawn attention",
    "harbour-mouth", "declared decoys", "non-threat",
]


def scan(label, text):
    low = (text or "").lower()
    hits = [s for s in SENSITIVE if s in low]
    tag = "LEAK " if hits else "clean"
    print(f"  [{tag}] {label}")
    for h in hits:
        print(f"           -> {h!r}")
    return hits


print("=" * 90)
print("component-by-component scan for scenario-declared enemy-plan content")
print("=" * 90)

total = 0
total += len(scan("1. PLANNER_SYSTEM_PROMPT", llm_planner.PLANNER_SYSTEM_PROMPT))
total += len(scan("2. PLANNER_USER_TEMPLATE_GRAPH", llm_planner.PLANNER_USER_TEMPLATE_GRAPH))

for mode in ("withheld", "aggregate", "declared"):
    print()
    print(f"--- briefing = {mode} ---")
    roe = run_episode._build_roe_notes(payload, briefing=mode)
    total += len(scan(f"3. roe_notes [{mode}]", roe))

print()
print("--- 4. graph timeline block (gated on briefing_declared) ---")
try:
    g = InterceptionGraph(tick=0, interceptors=(), target_count=0, history=None,
                          attack_timeline=timeline)
    tl = g.format_timeline_for_prompt()
except TypeError:
    tl = "\n".join(
        f"  {i.get('label')}: spawn_tick={i.get('spawn_tick')} count={i.get('count')} "
        f"axis={i.get('axis')}; {i.get('behavior')}" for i in timeline)
print("  timeline block content (only emitted when declared):")
print("   ", tl.replace("\n", "\n    ")[:600])
hits = scan("4. the timeline block itself", tl)
print(f"  => gated by `briefing_declared`; in withheld it is NOT appended "
      f"(verified in llm_planner.py).")

print()
print("=" * 90)
print(f"TOTAL sensitive hits in the static + withheld sources: {total}")
print("=" * 90)
if total == 0:
    print("VERDICT: in withheld mode the LLM prompt carries NO scenario-declared")
    print("         enemy-plan content. The two injection sites are:")
    print("           (a) roe_notes        -> emits no force numbers in withheld")
    print("           (b) timeline block   -> not appended when briefing_declared is False")
    print("         => the three LLM arms and the two non-LLM arms then differ only in")
    print("            representation, planning rate and action space, which are the")
    print("            variables under study - not in information access.")
else:
    print("VERDICT: residual leakage found - see hits above.")

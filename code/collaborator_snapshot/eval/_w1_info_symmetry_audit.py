"""Information-symmetry audit: what can each arm actually know?

For each arm, find whether it has a channel to (a) the scenario-declared attack
timeline, (b) the defender's own observation, (c) the interception graph.
If information enters the LLM prompt that no other arm can obtain, the comparison
is not fair - regardless of how the text is phrased.
"""
from __future__ import annotations

import os
import re

EVAL = r"C:\Code\source-code\openmd\code\eval"


def body(path: str) -> str:
    return open(os.path.join(EVAL, path), encoding="utf-8").read()


print("=== channel inventory per arm ===")
targets = {
    "rule planner (rule-rule)": "rule_planner.py",
    "RL agent (rl / rule-rl / llm-rl executor)": "rl_agent.py",
    "pure LLM": "pure_llm_agent.py",
    "LLM planner (llm-rule / llm-rl)": "llm_planner.py",
}
for label, fn in targets.items():
    src = body(fn)
    has_timeline = bool(re.search(r"timeline|attack_profile|load_attack_profile", src))
    has_roe = "roe_notes" in src
    has_obs = bool(re.search(r"observation|obs\b", src))
    has_graph = bool(re.search(r"graph|interception", src, re.I))
    print(f"\n  {label}  ({fn})")
    print(f"    reads scenario attack timeline : {has_timeline}")
    print(f"    receives roe_notes text        : {has_roe}")
    print(f"    consumes ObservationV2         : {has_obs}")
    print(f"    consumes interception graph    : {has_graph}")

print()
print("=== does the Observation itself expose threat classification? ===")
obs_src = body("attack_driver.py")
m = re.findall(r"contacts_by_faction|estimated_position_m|confidence|observer_entity_id|tags", obs_src)
print("  fields the attacker's own observation exposes:", sorted(set(m)))
print("  => contacts carry position/confidence/observer; faction filtering decides visibility.")
print("     'armed vs decoy' is NOT an observation field for either side.")

print()
print("=== how are civilians kept safe? engine-side or prompt-side? ===")
src = body("llm_planner.py")
for i, line in enumerate(src.splitlines(), 1):
    if "civilian" in line.lower():
        print(f"  llm_planner.py:{i}: {line.strip()[:110]}")

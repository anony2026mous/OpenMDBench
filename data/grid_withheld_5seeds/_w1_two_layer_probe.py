"""Compare, on the SAME observation, what the rule planner and the LLM planner emit.

Read-only: builds a session, steps it a few ticks, and dumps the GoalCommand[]
each planner produces.  The LLM planner holds the same fallback rule planner the
engine uses, so a missing endpoint shows up as fallback_used rather than a crash.
"""
from __future__ import annotations

import json
import os
import sys

EVAL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EVAL)

from goai_protocol import GOAL_TYPES, GoalCommand          # noqa: E402
from rule_planner import RulePlannerConfigV2, RulePlannerV2  # noqa: E402


def dump(cmd: GoalCommand) -> dict:
    return {
        "task_id": cmd.task_id,
        "goal_type": cmd.goal_type,
        "priority": cmd.priority,
        "deadline": cmd.deadline,
        "constraints": cmd.constraints,
        "parameters": {k: (round(v, 2) if isinstance(v, float) else v)
                       for k, v in sorted((cmd.parameters or {}).items())},
    }


print("=" * 92)
print("GOAL PROTOCOL - the shared vocabulary both planners must speak")
print("=" * 92)
print(f"GOAL_TYPES  ({len(GOAL_TYPES)}): {', '.join(GOAL_TYPES)}")
print()
print("GoalCommand fields:")
print("  task_id     str    e.g. 'intercept_017'  (pattern ^[a-z_]+_[0-9]{3}$)")
print("  goal_type   str    one of the 11 GOAL_TYPES")
print("  parameters  dict   unit_id / position / target_id / speed_mps / duration")
print("                     + per-type: axis_deg, radius_m, arc_deg (barrier)")
print("                                  standoff_m (ambush)")
print("                                  commit_within_m (reserve)")
print("  priority    float  default 0.5")
print("  constraints list   [{type, value}]")
print("  deadline    float? ticks from issue")
print("  issued_at   int    filled in by the broker, not the planner")
print()
print("GoalCommand.unit_id ->", GoalCommand.__dataclass_fields__["parameters"].default_factory.__name__,
      "lookup of parameters['unit_id']")

# ---------------------------------------------------------------- rule planner
print()
print("=" * 92)
print("RULE PLANNER  RulePlannerV2  (deterministic, no network)")
print("=" * 92)
cfg = RulePlannerConfigV2()
print("config fields:", ", ".join(f.name for f in cfg.__dataclass_fields__.values()))
rp = RulePlannerV2(cfg)
import inspect  # noqa: E402
print("plan signature:", inspect.signature(rp.plan))

# what goal types does the rule planner ever emit?
src = open(os.path.join(EVAL, "rule_planner.py"), encoding="utf-8").read()
emitted = sorted(set(__import__("re").findall(r'goal_type="([a-z_]+)"', src)))
print("goal_type literals in rule_planner.py:", emitted)
print("task_id prefixes:", sorted(set(__import__("re").findall(r'task_id=f?"([a-z_]+)_', src))))

# ------------------------------------------------------------- llm planner cfg
print()
print("=" * 92)
print("LLM PLANNER  LLMPlannerV2  (same output contract, LLM decides contents)")
print("=" * 92)
src2 = open(os.path.join(EVAL, "llm_planner.py"), encoding="utf-8").read()
emitted2 = sorted(set(__import__("re").findall(r'goal_type="([a-z_]+)"', src2)))
print("goal_type literals in llm_planner.py:", emitted2 or "(none - parsed from LLM JSON)")
print("has fallback planner:", "fallback_planner" in src2)
print("to_granularity applied:", "to_granularity" in src2)
print("command validation:", "validate" in src2 or "remap" in src2)

# ------------------------------------------------- broker / executor interface
print()
print("=" * 92)
print("DOWNSTREAM: how the executor consumes it")
print("=" * 92)
for name in ("v2_executor.py", "rl_executor.py"):
    s = open(os.path.join(EVAL, name), encoding="utf-8").read()
    print(f"-- {name}")
    print("   imports GoalCommand :", "GoalCommand" in s)
    for key in ("active_goals", "goals_for_unit", "by_unit", "goal_type"):
        if key in s:
            print(f"   uses {key!r}")
print()
print("RL executor act() signature:", end=" ")
s = open(os.path.join(EVAL, "rl_executor.py"), encoding="utf-8").read()
idx = s.find("def act(")
print(s[idx:s.find(":", idx) + 1].replace("\n", " "))
print("GOAI executor act() signature:", end=" ")
s = open(os.path.join(EVAL, "v2_executor.py"), encoding="utf-8").read()
idx = s.find("def act(")
print(s[idx:s.find(":", idx) + 1].replace("\n", " "))

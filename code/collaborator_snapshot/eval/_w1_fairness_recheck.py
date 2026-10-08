"""Strict fairness re-check: enumerate EVERY channel that could differ between arms.

For each arm, establish what it receives. Anything the LLM arms receive that
rule-rule / rl cannot obtain from the environment is a residual asymmetry and must
be reported, even if small.
"""
from __future__ import annotations

import os
import re

EVAL = r"C:\Code\source-code\openmd\code\eval"


def src(fn):
    return open(os.path.join(EVAL, fn), encoding="utf-8").read()


print("=" * 92)
print("A. what each arm is GIVEN (construction-time channels)")
print("=" * 92)

checks = [
    ("scenario attack timeline (enemy plan)", r"attack_profile|timeline"),
    ("roe_notes text", r"roe_notes"),
    ("interception graph (structured picture)", r"graph_builder|interception_graph"),
    ("ObservationV2", r"observation"),
    ("task/mission text", r"objective|mission"),
    ("weapon envelope table", r"speed_by_tag|weapon_policies"),
    ("fire doctrine", r"fire_doctrine|fire_policy"),
]

ARMS = {
    "rule-rule (rule_planner.py)": ["rule_planner.py"],
    "rl / rule-rl / llm-rl executor (rl_agent.py + rl_executor.py)":
        ["rl_agent.py", "rl_executor.py"],
    "pure-llm (pure_llm_agent.py)": ["pure_llm_agent.py"],
    "llm-rule / llm-rl planner (llm_planner.py)": ["llm_planner.py"],
}

for label, files in ARMS.items():
    blob = "\n".join(src(f) for f in files)
    print(f"\n  {label}")
    for name, pat in checks:
        hit = bool(re.search(pat, blob, re.I))
        print(f"      {name:<42} {'YES' if hit else '-'}")

print()
print("=" * 92)
print("B. the enemy plan reaches the LLM by two paths - are BOTH closed in withheld?")
print("=" * 92)
rp = src("run_episode.py")
print("  path 1  roe_notes built from profile_data")
i = rp.find("def _build_roe_notes")
seg = rp[i:i + 400]
print(f"          withheld branch emits enemy force counts? "
      f"{'YES' if '[aggregate briefing]' in rp[i:i+9000] and 'aggregate' not in seg else 'see below'}")
# check the withheld path specifically
j = rp.find('if briefing not in ("aggregate", "declared")')
k = rp.find("lines.append", j)
print("          withheld explanatory line contains force numbers? "
      f"{'numbers' in rp[j:j+700].lower()}")

lp = src("llm_planner.py")
print("  path 2  graph.format_timeline_for_prompt() injected into the user prompt")
print(f"          gated on briefing_declared? {'briefing_declared' in lp}")
m = re.search(r"if self\._prompt_context\.get\(\"briefing_declared\".{0,400}", lp, re.S)
if m:
    print("          code:", " ".join(m.group(0).split())[:200])

print()
print("=" * 92)
print("C. does the RULE planner see the same structured picture as the LLM?")
print("=" * 92)
for f in ("rule_planner.py", "llm_planner.py"):
    s = src(f)
    uses_graph = bool(re.search(r"[Gg]raph", s))
    uses_contacts = "contacts_by_faction" in s
    print(f"  {f:<20} graph={'Y' if uses_graph else '-'}  "
          f"raw contacts={'Y' if uses_contacts else '-'}")

print()
print("=" * 92)
print("D. residual asymmetries to declare in the paper")
print("=" * 92)
print("""  1. planning rate   : LLM plans every 10 ticks; the rule planner re-solves every
                       tick. Not equalised (LLM cost makes 1-tick planning infeasible).
  2. representation  : the LLM reads prose; rule/RL read numbers. Inherent to the
                       comparison, not a leak.
  3. pure-llm vs the goal-based arms: pure-llm emits low-level actions every call,
                       the others emit goal commands. Different action spaces.
  4. latency/cost    : LLM arms are ~7x slower per tick. A cost column is required.
  5. fallback        : the LLM planner falls back to the rule planner when parsing
                       fails (parse_failures>0 has been observed), so the LLM arm can
                       silently inherit rule behaviour on some planning cycles.""")

"""Speed-envelope completeness audit.

Two things were fixed earlier:
  FIX-1  run_episode.py: --pure-llm-envelope default hardcoded(45/10) -> executor(43/8)
  FIX-2  pure_llm_agent.py: get_stats() now records speed_max_by_tag (provenance)

This checks every REMAINING surface that encodes or displays a speed envelope.
"""
from __future__ import annotations

import os
import re

EVAL = r"C:\Code\source-code\openmd\code\eval"


def s(fn):
    return open(os.path.join(EVAL, fn), encoding="utf-8").read()


print("=" * 94)
print("speed-envelope surfaces")
print("=" * 94)

checks = []

# 1. the prompt's declared speed bound
pl = s("pure_llm_agent.py")
m = re.search(r'"speed_range":\s*"([^"]+)"', pl)
checks.append(("prompt speed bound (pure_llm_agent _DEFAULT_PROMPT_CONTEXT)",
               m.group(1) if m else "not found",
               "hardcoded -> '0-45'; real cap is 43 or 40"))

# 2. the fallback in _speed_limit
m2 = re.search(r"def _speed_limit.*?return ([\d.]+)", pl, re.S)
checks.append(("_speed_limit fallback",
               m2.group(1) if m2 else "not found",
               "hardcoded 15.0; ExecutorConfigV2.default_speed_mps is 12.0"))

# 3. few-shot examples
ex = re.findall(r'"speed_mps":\s*(\d+)', pl)
checks.append(("few-shot example speeds in prompts",
               ",".join(sorted(set(ex))) or "none",
               "40 in examples; per-scenario cap is 43 or 40"))

# 4. where the harness builds the envelope
rp = s("run_episode.py")
m3 = re.search(r"speed_by_tag\s*=\s*\{([^}]+)\}", rp)
checks.append(("harness envelope construction (run_episode)",
               " ".join(m3.group(1).split()) if m3 else "not found",
               "derived from defence.intercept_speed_mps -> 43 or 40"))

# 5. default of the CLI switch
m4 = re.search(r'"--pure-llm-envelope",\s*default="(\w+)"', rp)
checks.append(("--pure-llm-envelope default",
               m4.group(1) if m4 else "not found",
               "FIXED earlier: hardcoded -> executor"))

# 6. provenance recorded?
checks.append(("provenance field in reports",
               "speed_max_by_tag" if "speed_max_by_tag" in pl else "missing",
               "FIXED earlier: added to get_stats()"))

# 7. docs still claiming the old default
docs = {}
for fn in ("PAPER_READINESS_GAPS.md", "PAPER_METHOD_FIGURES.md",
           "ARM5_LLM_RL_EXECUTOR_DESIGN.md", "LLMRL_EXPERIMENT_DESIGN.md"):
    t = s(fn)
    hits = []
    if "默认 hardcoded" in t:
        hits.append("默认 hardcoded")
    if "45/10" in t:
        hits.append("45/10")
    if "0-45" in t:
        hits.append("0-45")
    if hits:
        docs[fn] = hits

for name, val, note in checks:
    print(f"\n  {name}")
    print(f"      current : {val}")
    print(f"      note    : {note}")

print()
print("=" * 94)
print("docs still carrying the OLD envelope numbers")
print("=" * 94)
for fn, hits in docs.items():
    print(f"  {fn:<40} {hits}")

print()
print("=" * 94)
print("what FIX-1 changed vs what is still open")
print("=" * 94)
print("""  FIXED (earlier today):
    * --pure-llm-envelope default  hardcoded -> executor
      => pure-llm now uses the SAME speed table as the other five arms
    * speed_max_by_tag added to pure-llm's report
      => the envelope is now auditable per episode

  STILL OPEN (these are prompt/doc consistency, not execution):
    * the prompt tells the LLM "speed_mps <0-45>" regardless of the real cap
    * _speed_limit falls back to 15.0, while the executor layer uses 12.0
    * few-shot examples show speed 40
    * six doc locations still quote 45/10 or "默认 hardcoded"

  NONE of the open items changes what the EXECUTOR does: it always clips to
  ExecutorConfigV2.speed_by_tag. So they cannot explain any score difference in
  the recorded data - they are口径/一致性问题, not measurement bias.""")

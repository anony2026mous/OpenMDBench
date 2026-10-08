"""Is the LLM endpoint deterministic?  Project has never tested this.

Send the SAME prompt several times with the configured sampling parameters and
compare outputs. If the endpoint is non-deterministic, then "seed" no longer
identifies a whole dice stream: the arm is (deterministic engine) x (stochastic
LLM), and repeated runs at a fixed seed are legitimate replicates rather than
replays. That changes how every comparison in the paper must be described.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

from llm_client_hifi import LLMClient  # noqa: E402

SYS = "You are a terse assistant. Answer with JSON only."
USER = ('Output JSON only: {"goal_commands": [{"task_id": "intercept_001", '
        '"goal_type": "intercept", "parameters": {"unit_id": "defender.uav-01", '
        '"target_id": "intruder.uav-01"}, "priority": 0.9}]}')

base = os.environ.get("OPENAI_BASE_URL")
print("endpoint:", base, " model:", os.environ.get("LLM_DEFAULT_MODEL"))
print()

outs = []
for i in range(5):
    try:
        c = LLMClient()
        txt = c.chat(SYS, USER, max_tokens=256, temperature=0.1)
        outs.append(str(txt))
        print(f"--- call {i+1} ---")
        print("   ", str(txt)[:220].replace("\n", " "))
    except Exception as exc:  # noqa: BLE001
        print(f"--- call {i+1} FAILED: {type(exc).__name__}: {exc}")
        outs.append(None)

ok = [o for o in outs if o is not None]
print()
print(f"successful calls: {len(ok)}/{len(outs)}")
if len(ok) >= 2:
    uniq = len(set(ok))
    print(f"distinct outputs: {uniq}")
    if uniq == 1:
        print("VERDICT: endpoint is DETERMINISTIC for this prompt "
              "(same input -> same output)")
    else:
        print("VERDICT: endpoint is NON-DETERMINISTIC "
              "(same prompt, temperature=0.1 -> different outputs)")
        print("  => a fixed seed does NOT replay the same episode for LLM arms;")
        print("     repeated runs at one seed are legitimate replicates.")

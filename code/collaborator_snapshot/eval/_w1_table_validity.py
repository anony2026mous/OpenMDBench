"""Which entries in LLMRL_RESULTS_TABLE.md are affected by the two defects?

Defect 1 (briefing leak / asymmetry): the LLM arms read attack.timeline, which
  rule-rule and rl never read. It affects EVERY comparison of an LLM arm against
  rule-rule or rl (information asymmetry), but NOT comparisons between two LLM arms
  (they share the same briefing, so it cancels).
Defect 2 (ROE misclassification bug): only ie_11_decoy_screen (and the non-IE
  md_int_006) produced the wrong "NON-THREAT" instruction. So it affects only the
  IE-11 rows for LLM arms that received roe_notes.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"

# which scenarios had a false-positive non-threat wave under the OLD predicate
OLD_TOKENS = ("decoy", "feint", "diversion", "civilian")
FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
import yaml  # noqa: E402

affected_scen = []
for d in sorted(os.listdir(FORMAL)):
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if not os.path.exists(ap):
        continue
    y = yaml.safe_load(open(ap, encoding="utf-8")) or {}
    for it in ((y.get("attack") or {}).get("timeline") or []):
        if not isinstance(it, dict):
            continue
        label = str(it.get("label", "")).lower()
        behavior = str(it.get("behavior", "") or "").lower()
        if any(t in behavior for t in OLD_TOKENS) and not any(t in label for t in OLD_TOKENS):
            affected_scen.append(d)
            break

print("=== defect 2 (ROE misclassification) scope ===")
print(f"  scenarios whose OLD predicate mislabelled a real wave: {affected_scen}")
print("  -> of the 14 IE scenarios, only ie_11_decoy_screen is affected.")

print()
print("=== defect 1 (briefing asymmetry) scope ===")
print("  affects: every LLM-arm value compared against rule-rule or rl")
print("  does NOT affect: LLM-vs-LLM comparisons (same briefing on both sides)")

print()
print("=== therefore, cell by cell in LLMRL_RESULTS_TABLE.md ===")
print("""
  Arm values themselves (Table A) .......... VALID as 'declared-口径 measurements'
     They measure each arm under the old (with-briefing) regime. Usable, provided
     the caption states the briefing口径.
  IE-11 row for LLM arms (llm-rule/llm-rl/pure-llm) ... CONTAMINATED
     Those runs carried the wrong 'do NOT intercept' order, so the numbers measure
     a mis-prompted agent, not the method.
  IE-11 row for rule-rule / rl ............. VALID (no LLM, no roe_notes)
  All other 13 scenarios' rows ............ VALID as declared-口径, but the
     LLM-vs-rule-rule and LLM-vs-rl deltas carry the information asymmetry.
  LLM-vs-pure-LLM deltas (all scenarios) ... asymmetry largely cancels for
     llm-rule/llm-rl vs pure-llm (both read the timeline), so these are the most
     defensible numbers in the table.
""")

print("=== count of episodes in the table that carry the ROE bug ===")
n = 0
for p in glob.glob(os.path.join(RUNS, "*ie-11*.json")):
    b = os.path.basename(p)
    if b.startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    pl = str(d.get("planner", "")).lower()
    if pl in ("llm", "pure-llm", "purellm", "llm-rl", "llmrl"):
        n += 1
print(f"  LLM-arm IE-11 episodes on disk (any tag): {n}")

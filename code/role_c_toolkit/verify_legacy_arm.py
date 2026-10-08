"""Legacy-arm verification using FILENAME arm tags (the archive's body field lies).

The archived declared-briefing snapshot names the PLANNING layer in the body, so an
in-body arm lookup folds every LLM+RL episode into LLM+Rule and reports zero LLM+RL.
The filename prefix (`ie_llmrl_...`) is the reliable tag for this vintage.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ARCHIVE = (Path.home() / "openmd_private_archive"
           / "declared_briefing_snapshot_20260927_1419" / "results")
PAPER = {"llm-rule": (0.769, 82), "llm-rl": (0.782, 49), "pure-llm": (0.516, 40)}


def walk(o):
    if isinstance(o, list):
        for x in o:
            yield from walk(x)
    elif isinstance(o, dict):
        if isinstance(o.get("strategy_scorecard"), dict):
            yield o
        else:
            for v in o.values():
                yield from walk(v)


def arm_from_name(stem: str):
    """Map the archive's filename prefix to a stack.

    The prefixes in this vintage are `ie_rule`, `ie_rulerl`, `ie_llmrl`,
    `ie_rl`, `ie_purellm`, `ie_llm` -- note `ie_llm` is the LLM-planner +
    RULE-executor stack, NOT a bare LLM, and there is no `ie_llmrule` prefix.
    """
    s = stem.lower()
    if s.startswith("ie_llmrl") or s.startswith("ie03_llmrl"):
        return "llm-rl"
    if s.startswith("ie_purellm"):
        return "pure-llm"
    if s.startswith("ie_llm_") or s.startswith("ie_llm-") or s == "ie_llm":
        return "llm-rule"
    if s.startswith("ie03_llm_"):
        return "llm-rule"
    if s.startswith("ie_rulerl"):
        return "rule-rl"
    if s.startswith("ie_rl_"):
        return "rl"
    if s.startswith("ie_rule_"):
        return "rule-rule"
    return None


rows: dict[str, list[float]] = {}
for p in sorted(ARCHIVE.glob("*.json")):
    a = arm_from_name(p.stem)
    if not a:
        continue
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        continue
    for r in walk(d):
        v = (r.get("strategy_scorecard") or {}).get("defender_score")
        if isinstance(v, (int, float)):
            rows.setdefault(a, []).append(float(v))

print("=" * 92)
print("appendix G legacy arm, arm tagged from FILENAME (archive body field is unreliable)")
print("=" * 92)

# The archive lives in the author's home directory and is NOT published, so this check
# cannot run from a fresh clone. It must say so and fail: printing `nan` over zero
# episodes and exiting 0 is indistinguishable from a pass, and it silently stopped
# checking anything the moment the archive name was redacted out of this file.
if not ARCHIVE.is_dir():
    print(f"  archive not present: {ARCHIVE}")
    print("  The legacy episodes are not redistributable, so this block is documented")
    print("  rather than reproduced here -- see data/PENDING.md.")
    raise SystemExit(2)

print(f"  {'stack':<11}{'n':>6}{'mean':>9}{'sd':>8}{'paper':>9}{'paper n':>9}{'diff':>9}")
mismatch = 0
for a in ("llm-rule", "llm-rl", "pure-llm"):
    vs = rows.get(a, [])
    pv, pn = PAPER[a]
    m = st.mean(vs) if vs else float("nan")
    sd = st.stdev(vs) if len(vs) > 1 else float("nan")
    # Only the mean is gated, and loosely. The episode counts differ from the printed n
    # because the table used a seed subset that is not recorded anywhere, and the means
    # differ by 0.01-0.03; that discrepancy is a documented divergence (data/PENDING.md),
    # not something this script should paper over.
    if vs and abs(m - pv) > 0.05:
        mismatch += 1
    print(f"  {a:<11}{len(vs):>6}{m:>9.3f}{sd:>8.3f}{pv:>9.3f}{pn:>9}{m - pv:>+9.3f}")
for a in sorted(rows):
    if a not in PAPER:
        print(f"  {a:<11}{len(rows[a]):>6}{st.mean(rows[a]):>9.3f}")

total = sum(len(rows.get(a, [])) for a in PAPER)
if not total:
    print("\n  no episodes read from the archive")
    raise SystemExit(2)
print(f"\n  episodes read: {total}; means off by more than 0.05: {mismatch}/3")
print("  (episode counts differ from the printed n -- see data/PENDING.md)")
raise SystemExit(1 if mismatch else 0)

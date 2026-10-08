"""Which scenario waves are mis-classified by _build_roe_notes, and how badly?

Reimplements the exact predicate from run_episode.py:_build_roe_notes:
    token match on the lower-cased "<label> <behavior>" blob
and reports:
  * waves containing a non-threat token ONLY in `behavior` (label is clean)
    -> these are the false positives: a real strike labelled non-threat
  * waves with a non-threat token in the LABEL
    -> intended classification
Also lists how many recorded LLM-arm episodes ran under a prompt containing a
false-positive non-threat declaration.
"""
from __future__ import annotations

import glob
import json
import os
from collections import defaultdict

import yaml

FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"
RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs"
TOKENS = ("decoy", "feint", "diversion", "civilian")

# public id per package dir (from scenario.yaml)
pub = {}
for d in os.listdir(FORMAL):
    sp = os.path.join(FORMAL, d, "scenario.yaml")
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if not (os.path.exists(sp) and os.path.exists(ap)):
        continue
    try:
        sid = (yaml.safe_load(open(sp, encoding="utf-8")).get("scenario") or {}).get("scenario_id")
    except Exception:  # noqa: BLE001
        sid = None
    if sid:
        pub[d] = str(sid).upper().replace(".V1", "").replace("-", "-")

print("=== per-scenario wave classification (exact _build_roe_notes predicate) ===")
false_pos: dict[str, list[str]] = {}
for d in sorted(os.listdir(FORMAL)):
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if not os.path.exists(ap):
        continue
    try:
        y = yaml.safe_load(open(ap, encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        continue
    tl = ((y.get("attack") or {}).get("timeline")) or []
    if not tl:
        continue
    fps = []
    for it in tl:
        if not isinstance(it, dict):
            continue
        label = str(it.get("label", it.get("role", "wave")))
        behavior = str(it.get("behavior", "") or "")
        blob = f"{label} {behavior}".lower()
        lab_l = label.lower()
        if not any(t in blob for t in TOKENS):
            continue
        in_label = any(t in lab_l for t in TOKENS)
        mark = "intended (token in LABEL)" if in_label else "FALSE POSITIVE (token only in behavior)"
        print(f"  {d:<34} label={label!r:<22} -> {mark}")
        if not in_label:
            fps.append(f"{label} (count={it.get('count')}, tick={it.get('spawn_tick')})")
    if fps:
        false_pos[d] = fps

print()
print("=== scenarios affected by a FALSE POSITIVE ===")
for d, fps in false_pos.items():
    print(f"  {d}: {fps}")
if not false_pos:
    print("  none")

print()
print("=== how many recorded LLM-arm episodes ran under such a prompt? ===")
affected_public = set()
for d in false_pos:
    # map package dir to the report's scenario string
    affected_public.add(d.replace("_", "-").replace("ie-", "IE-").upper())
cnt = defaultdict(int)
for p in glob.glob(os.path.join(RUNS, "*.json")):
    if os.path.basename(p).startswith("_"):
        continue
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict):
        continue
    sc = str(d.get("scenario", "")).upper()
    pl = str(d.get("planner", "")).lower()
    if sc in affected_public and pl in ("llm", "pure-llm", "purellm", "llm-rl", "llmrl"):
        cnt[pl] += 1
for k, v in sorted(cnt.items()):
    print(f"  {k:<10} {v} episodes")
print(f"  TOTAL affected LLM-arm episodes: {sum(cnt.values())}")

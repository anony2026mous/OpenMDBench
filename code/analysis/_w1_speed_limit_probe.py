"""Does the hardcoded 15.0 fallback ever fire, and what does _speed_limit return?

Enumerates every defender entity in the 14 IE scenarios through the real
platform_kind() + PureLLMAgentV2._speed_limit() logic, using the envelope the
harness would pass.
"""
from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import yaml

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

from v2_executor import ExecutorConfigV2, platform_kind  # noqa: E402
import pure_llm_agent  # noqa: E402

FORMAL = r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal"

SCEN = ["ie_01_single_target", "ie_02_dual_threat", "ie_03_surface_raid",
        "ie_04_combined_arms", "ie_05_multi_axis", "ie_06_decoy_mixed",
        "ie_07_cross_domain", "ie_08_island_strike", "ie_09_staggered_waves",
        "ie_10_dual_axis_pincer", "ie_11_decoy_screen", "ie_12_fog_onset",
        "ie_13_deep_strike", "ie_14_saturation_three_wave"]


def fake_view(ent):
    """Minimal stand-in exposing the attributes platform_kind()/is_fixed_platform read."""
    return SimpleNamespace(
        domain=str(ent.get("domain") or ""),
        tags=tuple(ent.get("tags") or ()),
        platform_ref=str(ent.get("platform_ref") or ent.get("platform") or ""),
        model_ref=str(ent.get("model_ref") or ""),
        is_fixed=bool(ent.get("is_fixed") or False),
    )


print(f"{'scenario':<28}{'entity':<30}{'kind':<8}{'limit':>7}  note")
fallback_hits = 0
total = 0
for d in SCEN:
    sp = os.path.join(FORMAL, d, "scenario.yaml")
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if not (os.path.exists(sp) and os.path.exists(ap)):
        continue
    y = yaml.safe_load(open(sp, encoding="utf-8")) or {}
    a = yaml.safe_load(open(ap, encoding="utf-8")) or {}
    speed = float(((a.get("defence") or {}).get("intercept_speed_mps")) or 40.0)
    envelope = {"uav": speed, "usv": 8.0, "interceptor": speed, "picket": 8.0}
    agent = pure_llm_agent.PureLLMAgentV2.__new__(pure_llm_agent.PureLLMAgentV2)
    agent.speed_max_by_tag = envelope

    for ent in ((y.get("scenario") or {}).get("entities") or []):
        fid = str(ent.get("faction_id") or "")
        if "defender" not in fid:
            continue
        tags = tuple(ent.get("tags") or ())
        view = fake_view(ent)
        kind = platform_kind(view)
        limit = agent._speed_limit(view, tags)
        total += 1
        hit = "FALLBACK 15.0" if abs(limit - 15.0) < 1e-9 and kind not in envelope \
            and not any(t in envelope for t in tags) else ""
        if hit:
            fallback_hits += 1
        print(f"{d:<28}{str(ent.get('entity_id')):<30}{kind:<8}{limit:>7.1f}  {hit}")

print()
print(f"defender entities scanned : {total}")
print(f"fallback-15.0 hits        : {fallback_hits}")
print()
print("=== also: what envelope does the harness actually pass per scenario? ===")
for d in SCEN:
    ap = os.path.join(FORMAL, d, "agents.yaml")
    if not os.path.exists(ap):
        continue
    a = yaml.safe_load(open(ap, encoding="utf-8")) or {}
    speed = ((a.get("defence") or {}).get("intercept_speed_mps"))
    print(f"  {d:<34} intercept_speed_mps={speed}  -> prompt says '0-45'")

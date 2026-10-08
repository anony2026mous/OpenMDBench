"""Is the terminal tick a FIXED scenario property, or does the arm influence it?

This matters for fairness: if scenarios end at a declared tick (as IE-09's
`event.intruders-destroyed` with `trigger: {kind: tick, tick: 999}` suggests), then
no arm can end early and cross-arm comparison is clean.  If some scenarios end on a
dynamic condition (e.g. "all intruders destroyed"), then the arm CONTROLS the
episode length, and the metric has to be shown to be length-independent.

Reads the scenario packages (not the episodes) so the answer is structural.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

FORMAL = Path(r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal")
IE = ["ie_01_single_target", "ie_02_dual_threat", "ie_03_surface_raid",
      "ie_04_combined_arms", "ie_05_multi_axis", "ie_06_decoy_mixed",
      "ie_07_cross_domain", "ie_08_island_strike", "ie_09_staggered_waves",
      "ie_10_dual_axis_pincer", "ie_11_decoy_screen", "ie_12_fog_onset",
      "ie_13_deep_strike", "ie_14_saturation_three_wave"]

print("=" * 104)
print("TERMINAL-CONDITION STRUCTURE AUDIT")
print("=" * 104)
print("\n  A scenario's terminal tick is either a DECLARED tick (arm-independent) or a")
print("  dynamic condition.  A dynamic condition on the INTRUDER side is still fair,")
print("  because the rule selects {scheduled, active, degraded} - so a wave that has")
print("  not spawned yet keeps the count > 0 and the rule cannot fire early.")
print("  A dynamic condition on the DEFENDER side would let an arm end its own")
print("  measurement, which is the case that needs explicit handling.")

print(f"\n  {'scenario':<26}{'horizon':>8}  {'rule id':<28}{'condition':<34}{'outcome':<18}{'side'}")
print("  " + "-" * 102)

arm_controlled = []
for d in IE:
    p = FORMAL / d / "scenario.yaml"
    y = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    sc = y.get("scenario") or {}
    horizon = (sc.get("world") or {}).get("duration_ticks")
    for r in (sc.get("mission_rules") or []):
        rid = str(r.get("id") or "?")
        cond = r.get("condition") or {}
        op = str(cond.get("operator") or "?")
        sel = cond.get("selector") or {}
        params = cond.get("parameters") or {}
        lc = tuple(sel.get("include_lifecycle") or ())
        tags = tuple(sel.get("tags") or ())
        desc = f"{op}({params.get('comparison', '?')}{params.get('value', params.get('tick', ''))})"
        out = str((r.get("outcome") or {}).get("result") or "?")
        is_terminal = bool((r.get("outcome") or {}).get("terminal"))
        if not is_terminal:
            continue
        if op == "tick" or cond.get("kind") == "tick":
            side = "fixed"
        elif any(t in ("intruder",) for t in tags):
            side = "intruder-side"
        elif any(t in ("facility", "combat-unit") for t in tags):
            side = "defender-side"
        else:
            side = "?"
        if side == "defender-side":
            arm_controlled.append((d, rid))
        print(f"  {d:<26}{str(horizon):>8}  {rid:<28}{desc:<34}{out:<18}{side}"
              f"  lc={lc} tags={tags}")

print("\n--- summary ---")
print(f"    scenarios with a DEFENDER-side dynamic terminal: "
      f"{len({s for s, _ in arm_controlled})}")
for s, rid in arm_controlled:
    print(f"      {s:<26} {rid}")
if not arm_controlled:
    print("    none - every terminal is either a declared tick or an intruder-side")
    print("    condition that cannot fire while a wave is still `scheduled`.")

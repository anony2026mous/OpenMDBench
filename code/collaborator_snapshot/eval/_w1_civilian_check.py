"""Which IE scenarios declare civilians, and what withheld emits for each."""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:\Code\source-code\openmd\code\eval")

import run_episode  # noqa: E402

SC = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
      "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
      "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
      "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
      "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]

print(f"{'scenario':<28}{'civ_count':>10}{'roe_lines':>11}")
for s in SC:
    p = run_episode.load_attack_profile_data(s)
    civ = p.get("civilian_lane") or {}
    n = int(civ.get("count") or 0) if isinstance(civ, dict) else 0
    txt = run_episode._build_roe_notes(p, briefing="withheld")
    print(f"{s:<28}{n:>10}{len(txt.splitlines()):>11}")
    if "civilian" in txt.lower():
        print("      ^ civilian guidance present")

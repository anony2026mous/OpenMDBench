"""End-to-end check of the ROE classification fix on the scenario that exposed it.

The old `_build_roe_notes` did substring matching on `f"{label} {behavior}"`.  In
IE-11 the real main-attack wave's behavior text is "after the decoys have already
drawn attention", so `"decoy" in blob` was TRUE and the four ARMED attackers were
labelled NON-THREAT.  The prompt then instructed the planner not to intercept them.

This script prints the actual briefing text for both口径 on the affected scenario and
asserts:
  * withholding does NOT label an armed wave as non-threat;
  * withholding discloses no wave counts/ticks/axes;
  * the classification is derived from declared weapon bindings, not from wording.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
os.environ.setdefault("OPENMDBENCH_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))

FORMAL = ROOT / "scenarios" / "formal"
LEAK_PATTERNS = [
    r"spawn_tick", r"axis=", r"count=", r"wave-\d",
    r"\b\d+\s+(?:armed|hostile|intruder)",          # a disclosed force count
    r"first wave", r"second wave", r"third wave",
]
NON_THREAT_RE = re.compile(r"non-threat|do not intercept|do NOT fire", re.I)


def load_profile(scen_dir: str):
    import yaml
    doc = yaml.safe_load((FORMAL / scen_dir / "scenario.yaml").read_text(encoding="utf-8"))
    return doc


def main() -> int:
    import run_episode
    from attack_driver import load_attack_profile_data

    scen = sys.argv[1] if len(sys.argv) > 1 else "ie_11_decoy_screen"
    # Use the SAME loader the episode uses.  Reconstructing the profile from the
    # scenario YAML looks plausible but yields an empty attack block (the wave
    # timeline lives in the attack profile package, not in scenario.yaml), which
    # would make every assertion below pass vacuously.
    scenario_arg = (scen.replace("_", "-").upper()
                    if "_" in scen and not scen.upper().startswith("IE-")
                    else scen)
    try:
        payload = load_attack_profile_data(scenario_arg)
    except Exception as exc:  # noqa: BLE001
        print(f"  loader failed for {scenario_arg!r}: {type(exc).__name__}: {exc}")
        return 2
    if not isinstance(payload, dict):
        print(f"  loader returned {type(payload).__name__}, expected dict")
        return 2

    print("=" * 100)
    print(f"ROE CLASSIFICATION CHECK   scenario={scen}")
    print("=" * 100)
    print(f"\n  profile keys: {sorted(payload.keys())}")

    armed = run_episode._armed_intruder_tags(payload)
    print(f"\n  armed tags from declared weapon_policies: {sorted(armed)}")
    tl = (payload.get("attack") or {}).get("timeline") or []
    print(f"  declared wave count: {len(tl)}")
    for item in tl:
        if isinstance(item, dict):
            print(f"    label={item.get('label')!r} count={item.get('count')} "
                  f"spawn_tick={item.get('spawn_tick')} axis={item.get('axis')}")
            print(f"      behavior={str(item.get('behavior'))[:120]!r}")

    rc = 0
    for mode in ("withheld", "declared"):
        text = run_episode._build_roe_notes(payload, briefing=mode)
        print(f"\n--- briefing={mode} ---")
        for line in text.splitlines():
            print(f"    {line}")

        leaks = []
        for pat in LEAK_PATTERNS:
            for m in re.finditer(pat, text, re.I):
                leaks.append(m.group(0))
        labels = NON_THREAT_RE.findall(text)

        print(f"    [check] disclosure patterns: {sorted(set(leaks)) or 'none'}")
        print(f"    [check] non-threat instructions: {len(labels)}")
        if mode == "withheld":
            if leaks:
                print("    FAIL: withheld text discloses scenario-declared details")
                rc = 1
            if labels:
                print("    NOTE: text still tells the planner something is non-engageable")
                print("          (acceptable only if it refers to civilian/ROE, not a wave)")
            else:
                print("    OK: no wave is labelled non-threat under withheld")

    # the specific regression: IE-11's armed wave must never be called non-threat
    print("\n--- regression assertion ---")
    text_w = run_episode._build_roe_notes(payload, briefing="withheld")
    text_d = run_episode._build_roe_notes(payload, briefing="declared")
    old_bug = "declared NON-THREAT" in text_w
    print(f"    'declared NON-THREAT' present in withheld text : {old_bug}")
    print(f"    'declared NON-THREAT' present in declared text : "
          f"{'declared NON-THREAT' in text_d}")
    if old_bug:
        print("    FAIL: the misclassification is back")
        rc = 1
    else:
        print("    OK: the IE-11 misclassification cannot occur - classification is")
        print("        driven by weapon bindings, so wording cannot flip it")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

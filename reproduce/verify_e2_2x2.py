"""Verify appendix G's "Experiment 2" (headroom-manipulation feasibility probe).

The paper (appendix.tex 165-168) states, for the probe behind §6.7:
  * Study 2 uses new runs, seeds 64101--64105, full plans vs. degraded (hold) plans
  * a 32-tier baseline scan located near-saturated tiers (scan range 0.17--1.00)
  * the full-vs-degraded effect is significant in 5/5 tiers, magnitude +0.62 to +0.73
  * a granularity probe (N013, seed 64101) collapses the tier to ~0.18 when only
    target_id is removed, and changes nothing when position/speed/pattern/constraints
    are removed (0.9692 both ways)
  * "Study 2 batch SHA-256-manifested (594 files)"
  * Data: e1_2x2_option1.json, e1_2x2_option2.json
  * the 2x2 interaction is NOT attributable to headroom (three stated reasons)

This checks each of those against the batch.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The batch root holds MANIFEST.json / option2_result.json alongside granprobe/,
# paired/, scan/ and smoke/ -- there is no `option2/` subdirectory.
B = ROOT / "data" / "e4-headroom-2x2"


def main() -> int:
    res_f = B / "option2_result.json"
    if not res_f.is_file():
        print(f"  batch not present: {B}")
        return 0
    d = json.loads(res_f.read_text(encoding="utf-8"))
    man = json.loads((B / "MANIFEST.json").read_text(encoding="utf-8"))

    print("=" * 96)
    print("appendix G 'Experiment 2'  vs  e1-2x2-option2 batch")
    print("=" * 96)
    print(f"  schema     : {d.get('schema')}")
    print(f"  file count : {sum(1 for _ in B.rglob('*') if _.is_file())}"
          f"   (paper says 'SHA-256-manifested (594 files)')")
    seeds = [c.get("seeds", []) for c in d.get("cells", []) if c.get("seeds")]
    print(f"  seeds      : {seeds[0] if seeds else '?'}   (paper: 64101--64105)")
    print(f"  score field: {man.get('design', {}).get('score_field')}")

    scan = d.get("scan", [])
    if scan:
        vs = [s["v"] for s in scan if isinstance(s.get("v"), (int, float))]
        print(f"\n  --- baseline scan: {len(scan)} tiers, V range "
              f"{min(vs):.4f} -- {max(vs):.4f}  (paper: 0.17--1.00) ---")

    print(f"\n  --- Study 2: full vs degraded, per tier ---")
    print(f"  {'tier':<34}{'n':>3}{'strong':>9}{'degraded':>10}{'effect':>9}")
    effs = []
    for c in d.get("cells", []):
        s, w = c.get("strong_mean"), c.get("reference_mean")
        if isinstance(s, (int, float)) and isinstance(w, (int, float)):
            effs.append(s - w)
            print(f"  {c['tier'].replace('COUNT-IE-05-MULTI-AXIS-','IE-05 '):<34}"
                  f"{c.get('n', 0):>3}{s:>9.4f}{w:>10.4f}{s - w:>+9.4f}")
    if effs:
        print(f"  effect range: {min(effs):+.4f} -- {max(effs):+.4f}"
              f"   (paper: +0.62 to +0.73)")

    inter = d.get("interaction", {})
    print(f"\n  --- 2x2 interaction ---")
    print(f"  value {inter.get('value'):+.4f}  CI "
          f"[{inter.get('ci_low'):+.4f}, {inter.get('ci_high'):+.4f}]  "
          f"significant={inter.get('significant')}")
    print(f"  withheld-arm range: {inter.get('withheld_arm_range')}"
          f"   (paper: degraded floor V ~ 0.18)")
    print(f"  caveat: {inter.get('caveat')}")

    # the granularity probe the paper describes
    gp = B / "granprobe"
    if gp.is_dir():
        print(f"\n  --- granularity probe (paper: N013/seed 64101, "
              f"~0.18 with only target_id removed, 0.9692 both ways) ---")
        for sub in sorted(gp.iterdir()):
            r = sub / "report.json"
            if r.is_file():
                rep = json.loads(r.read_text(encoding="utf-8"))
                v = (rep.get("layered_metrics") or {}).get("performance_v")
                print(f"     {sub.name:<10} performance_v = {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

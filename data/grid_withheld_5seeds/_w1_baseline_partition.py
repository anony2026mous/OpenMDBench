"""Group every candidate baseline episode by its POLICY identity.

`rl` is not one arm, it is a family: the archived results directory mixes several
checkpoints (`theta_rl_legacy2`, `theta_rl_main5`, `theta_rl_main4`, ...) that were
trained at different times with different speed conventions.  Averaging them would
produce a number belonging to no policy at all, and comparing an LLM arm against
that mixture would be meaningless.

So before any comparison, partition the baseline by (theta file, speed_source,
decision_interval) and report coverage per partition.  Then the analysis can pick a
single, provenance-clean partition - or the project can re-run the baseline under
one identity, which is the only way to get a bit-identical footing.
"""
from __future__ import annotations

import json
import os
import re
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "<private-archive>" / "declared_briefing_snapshot_20260927_1419" / "results"
RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")
SCEN = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
        "IE-04-COMBINED-ARMS", "IE-05-MULTI-AXIS", "IE-06-DECOY-MIXED",
        "IE-07-CROSS-DOMAIN", "IE-08-ISLAND-STRIKE", "IE-09-STAGGERED-WAVES",
        "IE-10-DUAL-AXIS-PINCER", "IE-11-DECOY-SCREEN", "IE-12-FOG-ONSET",
        "IE-13-DEEP-STRIKE", "IE-14-SATURATION-THREE-WAVE"]


def recomp(card):
    layers = card.get("layers") or {}
    wts = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = sum(float(layers[k]) * float(wts[k]) for k in wts
              if app.get(k, True) and k in layers)
    den = sum(float(wts[k]) for k in wts if app.get(k, True))
    return (num / den) if den else None


def score_of(d):
    card = d.get("strategy_scorecard") or {}
    raw = card.get("defender_score")
    if raw is None or int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        return None
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        return None
    rc = recomp(card)
    if rc is None or abs(float(raw) - rc) > 5e-4:
        return None
    return float(raw)


def meta_of(d, planner: str) -> dict:
    de = d.get("defender") or {}
    out = {}
    for blk in ("planner", "executor"):
        b = de.get(blk)
        if not isinstance(b, dict):
            continue
        for k in ("theta", "speed_source", "speed_source_provenance",
                  "checkpoint_meta", "obs_dim"):
            if k in b:
                out[k] = b[k]
        if out.get("theta"):
            break
    cm = out.get("checkpoint_meta")
    if isinstance(cm, dict):
        for k in ("decision_interval", "speed_source", "obs_dim"):
            if k in cm and k not in out:
                out[k] = cm[k]
    if planner == "rl" and out.get("obs_dim") != 2866 and "obs_dim" in out:
        return {"_reject": "obs_dim mismatch"}
    return out


def identity(m: dict, planner: str) -> str:
    theta = str(m.get("theta") or "?")
    name = Path(theta).name if theta != "?" else "?"
    if planner == "rl" and name in ("?", ""):
        return "rl:NO-THETA-RECORDED"
    src = str(m.get("speed_source") or "?")
    di = str(m.get("decision_interval") or "?")
    return f"{name} | speed={src} | interval={di}"


def main() -> int:
    planner = "rl"
    groups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counts: dict[str, int] = defaultdict(int)

    for p in list(SNAP.glob(f"ie_{planner}_*.json")) + list(RUNS.glob(f"ie_{planner}_*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict) or d.get("planner") != planner:
            continue
        sc = str(d.get("scenario") or "").upper()
        if sc not in SCEN:
            continue
        v = score_of(d)
        if v is None:
            continue
        m = meta_of(d, planner)
        if m.get("_reject"):
            counts["rejected: " + m["_reject"]] += 1
            continue
        groups[identity(m, planner)][sc].append(v)
        counts[identity(m, planner)] += 1

    print("=" * 108)
    print("BASELINE POLICY PARTITIONS  (planner=rl)")
    print("=" * 108)
    print(f"\n  {'partition':<58}{'n':>5}{'scen':>6}{'mean':>9}")
    for ident in sorted(groups, key=lambda k: -sum(len(v) for v in groups[k].values())):
        allv = [x for v in groups[ident].values() for x in v]
        print(f"  {ident:<58}{len(allv):>5}{len(groups[ident]):>6}{st.mean(allv):>9.4f}")

    print(f"\n  {'scenario':<28}" + "".join(
        f"{k[:14]:>16}" for k in sorted(groups, key=lambda k: -sum(
            len(v) for v in groups[k].values()))[:4]))
    top = sorted(groups, key=lambda k: -sum(len(v) for v in groups[k].values()))[:4]
    for sc in SCEN:
        row = f"  {sc:<28}"
        for k in top:
            v = groups[k].get(sc, [])
            row += f"{(f'{st.mean(v):.3f}(n={len(v)})' if v else '-'):>16}"
        print(row)

    print("\n--- verdict ---")
    biggest = top[0] if top else None
    if biggest:
        n = sum(len(v) for v in groups[biggest].values())
        cov = len(groups[biggest])
        print(f"    largest single-policy partition: {biggest}")
        print(f"      {n} episodes over {cov}/14 scenarios")
        if cov < 14:
            print("    => INSUFFICIENT coverage to serve as the baseline for all 14")
            print("       scenarios. Either restrict the comparison to the covered")
            print("       scenarios, or re-run the baseline under ONE policy identity")
            print("       so it is bit-identical in footing with the LLM arms.")
    print("\n    Any table that averages across partitions is reporting a number")
    print("    that belongs to no actual policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

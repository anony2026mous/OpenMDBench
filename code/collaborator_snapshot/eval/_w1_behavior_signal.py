"""Did withholding intelligence actually change behaviour?

The口径 switch is only meaningful if it changes what the planner knows.  This probe
compares decoy/threat firing behaviour between the archived `declared` episodes and
the new `withheld` episodes, per scenario and arm.

Why these fields: `fires_decoy` / `fires_civilian` / `fires_threat` and
`threat_neutralization_rate` come from the engine's own ROE bookkeeping, i.e. the
engine decides which contact was a decoy - not the planner, and not the prompt.  So
they measure the CONSEQUENCE of the information difference rather than restating it.

A null result here would be a finding too: it would mean the withheld情报 did not
change engagement choices, and the declared/withheld columns should then agree.
Either way, this has to be reported rather than assumed.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "openmd_private_archive" / "declared_briefing_snapshot_20260927_1419" / "results"
RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")

FIELDS = ["fires_decoy", "fires_threat", "fires_civilian", "first_fire_tick",
          "threat_neutralization_rate", "intruder_neutralized_count",
          "intruder_total_count", "defender_survival_rate", "ammo_efficiency"]


def norm_briefing(d) -> str | None:
    de = d.get("defender") or {}
    b = de.get("briefing")
    if b is None and isinstance(de.get("planner"), dict):
        b = de["planner"].get("briefing")
    return b if isinstance(b, str) else None


def key(d):
    return (str(d.get("scenario") or "").upper(), str(d.get("planner") or ""))


def usable(d) -> bool:
    card = d.get("strategy_scorecard") or {}
    return (int(d.get("ticks_run") or 0) > 0
            and not d.get("aborted")
            and (card.get("terminal") or {}).get("outcome") not in (None, "undecided")
            and card.get("defender_score") is not None)


decl: dict[tuple, list] = defaultdict(list)
withh: dict[tuple, list] = defaultdict(list)

for p in SNAP.glob("*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or d.get("planner") not in ("llm", "llm-rl"):
        continue
    if usable(d):
        decl[key(d)].append(d)

for p in RUNS.glob("*_n3*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or d.get("planner") not in ("llm", "llm-rl", "pure-llm"):
        continue
    if usable(d) and norm_briefing(d) == "withheld":
        withh[key(d)].append(d)

print("=" * 108)
print("BEHAVIOURAL SIGNAL: declared vs withheld, engine-side ROE bookkeeping")
print("=" * 108)
print(f"  archived declared episodes : {sum(len(v) for v in decl.values())}")
print(f"  new withheld episodes      : {sum(len(v) for v in withh.values())}")

print(f"\n  {'scenario':<28}{'arm':<9}{'n_d':>4}{'n_w':>4}"
      f"{'decoy_d':>9}{'decoy_w':>9}{'thr_d':>8}{'thr_w':>8}"
      f"{'fft_d':>8}{'fft_w':>8}{'tnr_d':>8}{'tnr_w':>8}")


def mean_field(rows, f):
    vals = [r.get("layered_metrics", {}).get(f) for r in rows]
    vals = [float(v) for v in vals if isinstance(v, (int, float))]
    return st.mean(vals) if vals else None


def fmt(v, w=8, p=2):
    return f"{v:>{w}.{p}f}" if v is not None else f"{'-':>{w}}"


for k in sorted(set(decl) | set(withh)):
    a, b = decl.get(k, []), withh.get(k, [])
    row = (f"  {k[0]:<28}{k[1]:<9}{len(a):>4}{len(b):>4}")
    for f in ("fires_decoy", "fires_threat", "first_fire_tick",
              "threat_neutralization_rate"):
        row += fmt(mean_field(a, f)) + fmt(mean_field(b, f))
    print(row)

print("\n  legend: decoy=fires_decoy, thr=fires_threat, fft=first_fire_tick,")
print("          tnr=threat_neutralization_rate;  _d=declared, _w=withheld")

print("\n--- aggregate where both口径 exist ---")
for arm in ("llm", "llm-rl"):
    for f in ("fires_decoy", "fires_threat", "threat_neutralization_rate"):
        a = [x for kk, v in decl.items() if kk[1] == arm for x in v]
        b = [x for kk, v in withh.items() if kk[1] == arm for x in v]
        ma, mb = mean_field(a, f), mean_field(b, f)
        if ma is None or mb is None:
            continue
        print(f"    {arm:<9}{f:<32} declared={ma:8.3f}  withheld={mb:8.3f}  "
              f"delta={mb - ma:+8.3f}")

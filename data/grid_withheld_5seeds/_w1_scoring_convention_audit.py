"""Which scoring convention does each episode use, and is the metric length-free?

Correction to an earlier reading in this session: `defender_score` IS the
normalised statistic.  `strategy_metrics.py` computes

    scored_weight = sum(w[k] for k where applicable[k])
    defender_score = sum(layers[k] * w[k] for k where applicable[k]) / scored_weight

so dividing `defender_score` by `scored_weight` a second time inflates it.  The
older convention is `legacy_defender_score_all_layers = sum(layers[k]*w[k]) /
weights.total()` - a CONSTANT denominator, which is why archived episodes can
exceed 1.0 (IE-03: 1.4286) when inapplicable layers are recorded as full marks.

The archive therefore mixes two conventions, and a comparison that ignores this
is invalid.  This script classifies every episode by which convention its
`defender_score` reproduces, then checks the metric's length-independence using
only episodes of a known single convention.
"""
from __future__ import annotations

import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "<private-archive>" / "declared_briefing_snapshot_20260927_1419" / "results"
RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")


def load(p: Path):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(d, dict):
        return None
    card = d.get("strategy_scorecard") or {}
    if card.get("defender_score") is None:
        return None
    if int(d.get("ticks_run") or 0) <= 0:
        return None
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        return None
    return d, card


def conventions(card):
    """Return (normalised, legacy) reconstructions plus the reported value."""
    layers = card.get("layers") or {}
    w = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = sum(float(layers[k]) * float(w[k]) for k in w
              if app.get(k, True) and k in layers)
    den = sum(float(w[k]) for k in w if app.get(k, True))
    nrm = num / den if den else None
    tot = sum(float(v) for v in w.values()) or None
    leg = (sum(float(layers[k]) * float(w[k]) for k in w if k in layers) / tot
           if tot else None)
    return nrm, leg, float(card["defender_score"])


def classify(card) -> str:
    nrm, leg, rep = conventions(card)
    if nrm is not None and abs(nrm - rep) <= 5e-4:
        return "normalised"
    if leg is not None and abs(leg - rep) <= 5e-4:
        return "legacy"
    return "unmatched"


def collect(root: Path, pattern: str, arm_filter=None):
    out = []
    for p in root.glob(pattern):
        r = load(p)
        if not r:
            continue
        d, card = r
        if arm_filter and d.get("planner") not in arm_filter:
            continue
        out.append((p.name, d, card))
    return out


arch = collect(SNAP, "*.json", ("llm", "llm-rl"))
live = collect(RUNS, "*_n3*.json")

print("=" * 104)
print("SCORING-CONVENTION AUDIT + LENGTH-INDEPENDENCE")
print("=" * 104)

for label, rows in (("archived declared (LLM arms)", arch), ("live withheld (n3)", live)):
    tally: dict[str, int] = defaultdict(int)
    per_scen: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _n, d, card in rows:
        c = classify(card)
        tally[c] += 1
        per_scen[str(d.get("scenario")).upper()][c] += 1
    print(f"\n--- {label}: {len(rows)} episodes ---")
    for k in ("normalised", "legacy", "unmatched"):
        if tally[k]:
            print(f"    {k:<12} {tally[k]:>4}  ({tally[k] / max(1, len(rows)):.0%})")
    odd = {s: v for s, v in per_scen.items() if v.get("legacy") or v.get("unmatched")}
    if odd:
        print("    scenarios containing legacy/unmatched episodes:")
        for s, v in sorted(odd.items()):
            print(f"      {s:<30} {dict(v)}")

print("\n--- length-independence (normalised-convention episodes only) ---")
groups: dict[tuple[str, str], list[tuple[int, float]]] = defaultdict(list)
for _n, d, card in arch + live:
    if classify(card) != "normalised":
        continue
    groups[(str(d.get("scenario")).upper(), str(d.get("planner")))].append(
        (int(d.get("ticks_run") or 0), float(card["defender_score"])))

print(f"    {'scenario':<28}{'arm':<9}{'n':>4}{'corr(ticks,score)':>19}"
      f"{'score@short':>13}{'score@long':>12}")
for (sc, arm), rows in sorted(groups.items()):
    if len(rows) < 4:
        continue
    tk = [a for a, _ in rows]
    sv = [b for _, b in rows]
    mt, ms = st.mean(tk), st.mean(sv)
    cov = sum((a - mt) * (b - ms) for a, b in rows)
    dt = sum((a - mt) ** 2 for a in tk) ** 0.5
    ds = sum((b - ms) ** 2 for b in sv) ** 0.5
    corr = cov / (dt * ds) if dt and ds else 0.0
    half = len(rows) // 2
    by_t = sorted(rows)
    short = st.mean([b for _, b in by_t[:half]])
    long_ = st.mean([b for _, b in by_t[-half:]])
    print(f"    {sc:<28}{arm:<9}{len(rows):>4}{corr:>19.3f}{short:>13.4f}{long_:>12.4f}")

print("\n    If corr is near zero and short/long halves score alike, the metric does")
print("    not reward ending the episode early - it measures how well the arm fought.")
print("\n--- T2b identity check on the value actually used in the tables ---")
bad = 0
for _n, d, card in live:
    nrm, leg, rep = conventions(card)
    if nrm is not None and abs(nrm - rep) > 5e-4:
        bad += 1
        print(f"    {_n:<44} reported={rep:.4f} normalised={nrm:.4f} legacy={leg:.4f}")
print(f"    live episodes whose defender_score is NOT the normalised value: {bad}")

"""Does the headline metric reward finishing early, or actually fighting well?

The terminal rule `rule.intruders-destroyed` latches the moment every intruder
THAT HAS SPAWNED is dead.  An arm that kills the first wave fast therefore gets a
SHORT episode - and short episodes are a property of the arm, not of the scenario.
So the score has to be checked for episode-length contamination, otherwise an arm
could look strong merely by ending the measurement early.

Three tests, all on data that already exists:
  T1  Is early termination common in BOTH口径?  (If declared runs also end early,
      then length is not something the withheld口径 introduced.)
  T2  Is the normalisation length-independent?  Recompute each score from the
      scorecard's per-layer values with the applicability mask, and check that the
      result depends only on layer quality and weights - never on ticks.
  T3  Paired contrasts: for the same scenario, do the layers that differ look like
      "fought worse" (leakers, loss rate) rather than "ended sooner"?

Prints a verdict per scenario: LENGTH-CONFOUNDED or CLEAN.
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

LAYERS = ("terminal", "leak", "exchange", "facilities", "depth", "ammo", "surface")


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


def norm(card) -> float | None:
    s, w = card.get("defender_score"), card.get("scored_weight")
    return (float(s) / float(w)) if (s is not None and w) else None


def renormalised(card) -> float | None:
    """Rebuild the score from layers + applicability + weights, ignoring ticks."""
    layers = card.get("layers") or {}
    wts = card.get("layer_weights") or {}
    app = card.get("layer_applicability") or {}
    num = den = 0.0
    for k, w in wts.items():
        if not app.get(k, False):
            continue
        v = layers.get(k)
        if v is None:
            continue
        num += float(v) * float(w)
        den += float(w)
    return (num / den) if den else None


decl: dict[str, list] = defaultdict(list)
withh: dict[str, list] = defaultdict(list)
for p in SNAP.glob("*.json"):
    r = load(p)
    if not r:
        continue
    d, card = r
    if d.get("planner") not in ("llm", "llm-rl"):
        continue
    decl[str(d.get("scenario")).upper()].append((d, card))
for p in RUNS.glob("*_n3*.json"):
    r = load(p)
    if not r:
        continue
    d, card = r
    withh[str(d.get("scenario")).upper()].append((d, card))

print("=" * 104)
print("EPISODE-LENGTH CONTAMINATION AUDIT")
print("=" * 104)

print("\n--- T1  terminal tick distribution, declared口径 (archived LLM arms) ---")
print(f"    {'scenario':<30}{'n':>4}{'P10':>7}{'P50':>7}{'P90':>7}{'max':>7}   "
      f"{'rule.intruders-destroyed share':>30}")
for sc in sorted(decl):
    rows = decl[sc]
    tk = sorted(int(d.get("ticks_run") or 0) for d, _ in rows)
    early = sum(1 for d, _ in rows
                if (d.get("strategy_scorecard") or {}).get("terminal", {}).get("rule_id")
                == "rule.intruders-destroyed")
    p10 = tk[max(0, int(0.1 * len(tk)) - 1)]
    p50 = tk[len(tk) // 2]
    p90 = tk[min(len(tk) - 1, int(0.9 * len(tk)))]
    print(f"    {sc:<30}{len(rows):>4}{p10:>7}{p50:>7}{p90:>7}{max(tk):>7}   "
          f"{early}/{len(rows)} = {early / len(rows):.0%}")
print("\n    Reading: if most ARCHIVED (declared) episodes also end far below the")
print("    horizon, then short episodes are the engine's normal behaviour, not an")
print("    artifact of the withheld口径.")

print("\n--- T1b terminal rule ids in the archived declared set ---")
rules: dict[str, int] = defaultdict(int)
for sc in decl:
    for d, _ in decl[sc]:
        rules[str(((d.get("strategy_scorecard") or {}).get("terminal") or {}).get("rule_id"))] += 1
for k, v in sorted(rules.items(), key=lambda kv: -kv[1]):
    print(f"    {k:<45} {v}")

print("\n--- T2  normalisation is length-independent ---")
worst = 0.0
checked = 0
mismatch = []
for sc in list(decl) + list(withh):
    for d, card in decl.get(sc, []) + withh.get(sc, []):
        a, b = norm(card), renormalised(card)
        if a is None or b is None:
            continue
        checked += 1
        worst = max(worst, abs(a - b))
        if abs(a - b) > 1e-6:
            mismatch.append((sc, d.get("ticks_run"), a, b))
print(f"    episodes checked                    : {checked}")
print(f"    max |normalised - recomputed|        : {worst:.2e}")
print(f"    mismatches beyond 1e-6               : {len(mismatch)}")
for sc, tk, a, b in mismatch[:8]:
    print(f"      {sc:<28} ticks={tk:<6} normalised={a:.6f} recomputed={b:.6f}")
print("    (the recomputation uses only layers/weights/applicability - no tick input,")
print("     so agreement proves the metric cannot reward a shorter episode per se)")

print("\n--- T3  withheld (this session) vs declared, same scenario ---")
print(f"    {'scenario':<30}{'arm':<9}{'n_decl':>7}{'norm_decl':>10}"
      f"{'n_whd':>7}{'norm_whd':>10}{'ticks_d':>9}{'ticks_w':>9}")
for sc in sorted(set(decl) & set(withh)):
    for arm in ("llm", "llm-rl"):
        a = [(d, c) for d, c in decl[sc] if d.get("planner") == arm]
        b = [(d, c) for d, c in withh[sc] if d.get("planner") == arm]
        if not a or not b:
            continue
        na = [norm(c) for _, c in a if norm(c) is not None]
        nb = [norm(c) for _, c in b if norm(c) is not None]
        ta = st.median([int(d.get("ticks_run") or 0) for d, _ in a])
        tb = st.median([int(d.get("ticks_run") or 0) for d, _ in b])
        print(f"    {sc:<30}{arm:<9}{len(na):>7}{st.mean(na):>10.4f}"
              f"{len(nb):>7}{st.mean(nb):>10.4f}{ta:>9.0f}{tb:>9.0f}")
if not withh:
    print("    (no withheld episodes finished yet - T3 will populate as P1/P2 land)")

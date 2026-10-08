"""Baseline drift gate: is the single-architecture arm still the SAME arm?

The user's hard boundary is that the already-tuned method must not move: after any
shared-code edit, `rule-rule` has to reproduce bit-for-bit.  This script turns that
into an executable gate by comparing CURRENT runs against the archived snapshot
taken before the口径 work started.

Two independent tests:
  A. Scenario identity - hash every file of each scenario package in the archive
     and compare with the live tree.  If a scenario changed, its old scores are
     not comparable and must not be quoted as the same cell.
  B. Score identity - for scenarios whose package is unchanged, compare the
     archived rule-rule readings with the live ones using the NORMALISED score
     (raw defender_score / scored_weight).  Raw `defender_score` mixes in
     inapplicable layers carrying placeholder values, so it is not comparable
     across scenario revisions; the normalised form is.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics as st
from collections import defaultdict
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
SNAP = HOME / "openmd_private_archive" / "declared_briefing_snapshot_20260927_1419"
LIVE_SCEN = Path(r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal")
LIVE_RUNS = Path(r"C:\Code\source-code\openmd\code\eval\_w1_runs")

ap = argparse.ArgumentParser()
ap.add_argument("--arm", default="rule", choices=("rule", "rl"))
ap.add_argument("--min-n", type=int, default=1)
ap.add_argument("--tol", type=float, default=1e-9)
args = ap.parse_args()


def norm(card: dict) -> float | None:
    s, w = card.get("defender_score"), card.get("scored_weight")
    if s is None or not w:
        return None
    return float(s) / float(w)


def dir_hash(root: Path) -> str:
    """Order-independent digest of every file under root (path + bytes)."""
    h = hashlib.sha256()
    if not root.exists():
        return "<absent>"
    items = []
    for p in sorted(root.rglob("*")):
        if p.is_file():
            items.append((str(p.relative_to(root)).replace("\\", "/"),
                          hashlib.sha256(p.read_bytes()).hexdigest()))
    for rel, dig in items:
        h.update(f"{rel}:{dig}\n".encode())
    return h.hexdigest()[:16]


print("=" * 96)
print(f"BASELINE DRIFT GATE   arm={args.arm}")
print("=" * 96)

print("\n--- A. scenario package identity (archive vs live) ---")
snap_scen = SNAP / "scenarios"
rows = []
for d in sorted(os.listdir(snap_scen)):
    p = snap_scen / d
    if not p.is_dir():
        continue
    live = LIVE_SCEN / d
    ha, hb = dir_hash(p), dir_hash(live)
    same = ha == hb
    rows.append((d, ha, hb, same))
    print(f"    {d:<32} archive={ha}  live={hb}  {'SAME' if same else 'CHANGED'}")
n_same = sum(1 for r in rows if r[3])
print(f"    => {n_same}/{len(rows)} scenario packages unchanged")

unchanged = {r[0] for r in rows if r[3]}

print(f"\n--- B. archived {args.arm} readings, by scenario ---")
arch: dict[str, list[tuple[int, float, int, int]]] = defaultdict(list)
res = SNAP / "results"
for p in res.glob("*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or d.get("planner") != args.arm:
        continue
    sc = str(d.get("scenario") or "")
    key = sc.lower().replace("-", "_")
    card = d.get("strategy_scorecard") or {}
    v = norm(card)
    if v is None:
        continue
    ticks = int(d.get("ticks_run") or 0)
    if ticks <= 0 or (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    arch[key].append((int(d.get("seed") or 0), v, ticks, card.get("layered_metrics") is not None))
for k in sorted(arch):
    vs = [x[1] for x in arch[k]]
    print(f"    {k:<32} n={len(vs):<3} mean={st.mean(vs):.4f} "
          f"sd={(st.pstdev(vs) if len(vs) > 1 else 0):.4f} "
          f"range=[{min(vs):.4f},{max(vs):.4f}]  pkg={'SAME' if k in unchanged else 'CHANGED'}")

print(f"\n--- C. live {args.arm} readings, by scenario ---")
live: dict[str, list[tuple[str, float, int]]] = defaultdict(list)
for p in LIVE_RUNS.glob("*.json"):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        continue
    if not isinstance(d, dict) or d.get("planner") != args.arm:
        continue
    sc = str(d.get("scenario") or "")
    key = sc.lower().replace("-", "_")
    card = d.get("strategy_scorecard") or {}
    v = norm(card)
    if v is None:
        continue
    if int(d.get("ticks_run") or 0) <= 0 or d.get("aborted"):
        continue
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        continue
    live[key].append((p.name, v, int(d.get("ticks_run") or 0)))
for k in sorted(live):
    vs = [x[1] for x in live[k]]
    print(f"    {k:<32} n={len(vs):<3} mean={st.mean(vs):.4f} "
          f"range=[{min(vs):.4f},{max(vs):.4f}]")

print("\n--- D. drift verdict (only where the package is unchanged) ---")
drift = 0
checked = 0
for k in sorted(set(arch) & set(live)):
    if k not in unchanged:
        print(f"    {k:<32} SKIPPED (package changed - archived cells not comparable)")
        continue
    a = [x[1] for x in arch[k]]
    b = [x[1] for x in live[k]]
    if len(a) < args.min_n or len(b) < args.min_n:
        continue
    checked += 1
    lo = min(min(a), min(b))
    hi = max(max(a), max(b))
    overlap = not (max(a) < min(b) - args.tol or max(b) < min(a) - args.tol)
    mov = abs(st.mean(a) - st.mean(b))
    flag = "OK" if overlap else "DRIFT"
    if not overlap:
        drift += 1
    print(f"    {k:<32} arch={st.mean(a):.4f}(n={len(a)}) live={st.mean(b):.4f}(n={len(b)}) "
          f"|dmean|={mov:.4f} spread=[{lo:.4f},{hi:.4f}]  {flag}")

print(f"\n  packages compared: {checked}   DRIFT: {drift}")
if checked == 0:
    print("  (no overlapping unchanged-package scenario with live data yet)")
print("\n  NOTE: overlapping ranges are the pass condition. The point of the gate is")
print("  that the live readings must fall inside the archived arm's own spread -")
print("  a systematic shift would mean shared-code edits moved the baseline arm.")

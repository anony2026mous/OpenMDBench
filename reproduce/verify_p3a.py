"""Verify appendix I.3 / tab_p3aseed against the P3a batch, from the raw episodes.

Reads each seed's six sub-runs and recomputes the table: LLM, hold, rule composites,
the two contrasts, and the LLM request count. Also checks the batch's own analysis.json
so a reader can see the two independent paths agree.
"""
from __future__ import annotations

import hashlib
import json
import statistics as st
from pathlib import Path

# Resolve relative to the repository so this runs from any checkout. The P3a batch arrives
# inside the co-author's p0-strengthening delivery.
_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent if (_HERE.parent / "data").is_dir() else _HERE
BASE = (_ROOT / "data" / "collaborator_runs" / "p0-strengthening-20261001"
        / "inputs" / "P3a__llm_goal_causal__s601-610__confirm__v1")

PAPER = {  # seed: (LLM, hold, rule, llm_calls)
    601: (1.000, 0.200, 1.000, 15), 602: (0.233, 0.200, 1.000, 11),
    603: (1.000, 0.200, 0.933, 15), 604: (0.933, 0.200, 1.000, 15),
    605: (0.400, 0.233, 0.933, 8),   606: (1.000, 0.200, 0.933, 15),
    607: (0.233, 0.200, 0.867, 10),  608: (0.233, 0.200, 0.233, 8),
    609: (0.933, 0.200, 0.933, 15),  610: (0.267, 0.200, 1.000, 15),
}
PAPER_PRIMARY = (0.420, 0.200, 0.637)
PAPER_SECONDARY = -0.260

# The batch's own analysis, used for the authoritative LLM-call counts.
ANALYSIS_ROWS: list[dict] = []
_ap = BASE / "analysis.json"
if _ap.exists():
    try:
        ANALYSIS_ROWS = json.loads(_ap.read_text(encoding="utf-8")).get("rows", [])
    except (OSError, ValueError):
        ANALYSIS_ROWS = []


def score(path: Path):
    """Composite V of an episode file, tolerating either report shape."""
    d = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(d.get("V"), (int, float)):
        return float(d["V"]), d
    sc = d.get("strategy_scorecard")
    if isinstance(sc, dict) and isinstance(sc.get("defender_score"), (int, float)):
        return float(sc["defender_score"]), d
    m = d.get("metrics")
    if isinstance(m, dict) and isinstance(m.get("blue_score"), (int, float)):
        return float(m["blue_score"]), d
    return None, d


def episode_in(sub: Path):
    for cand in ("episode.json", "report.json"):
        p = sub / cand
        if p.exists():
            return p
    hits = list(sub.glob("*.json"))
    return hits[0] if hits else None


print("=" * 100)
print("appendix I.3 / tab_p3aseed  vs  P3a batch raw episodes")
print("=" * 100)

rows = []
for seed in sorted(PAPER):
    sd = BASE / f"seed-{seed}"
    vals = {}
    for label, sub in (("llm", "llm_original"), ("hold", "llm_goals_to_hold"),
                       ("rule", "rule_planner")):
        p = episode_in(sd / sub) if (sd / sub).is_dir() else None
        vals[label] = score(p)[0] if p else None
    # LLM request count: take the batch's own field. Counting requests.jsonl lines
    # double-counts, because the file interleaves one record per request AND reply
    # (30 lines for 15 requests) -- measured, not assumed.
    calls = None
    p = episode_in(sd / "llm_original") if (sd / "llm_original").is_dir() else None
    for row in ANALYSIS_ROWS:
        if row.get("seed") == seed and isinstance(row.get("llm_requests"), int):
            calls = row["llm_requests"]
            break
    if calls is None and p:
        d = json.loads(p.read_text(encoding="utf-8"))
        for k in ("llm_requests", "requests", "n_requests", "llm_calls"):
            if isinstance(d.get(k), int):
                calls = d[k]
                break
    rows.append((seed, vals, calls))

print(f"  {'seed':<6}{'LLM':>8}{'hold':>8}{'rule':>8}{'L-hold':>9}{'L-rule':>9}"
      f"{'calls':>7}   paper (LLM/hold/rule/calls)")
bad = 0
for seed, vals, calls in rows:
    pl, ph, pr, pc = PAPER[seed]
    L, H, R = vals["llm"], vals["hold"], vals["rule"]
    if None in (L, H, R):
        print(f"  {seed:<6}  MISSING  {vals}")
        bad += 1
        continue
    dh, dr = L - H, L - R
    ok = (abs(L - pl) <= 0.001 and abs(H - ph) <= 0.001 and abs(R - pr) <= 0.001)
    if not ok:
        bad += 1
    flag = "" if ok else "  <-- DIFFERS"
    print(f"  {seed:<6}{L:>8.3f}{H:>8.3f}{R:>8.3f}{dh:>+9.3f}{dr:>+9.3f}"
          f"{(calls if calls is not None else -1):>7}   {pl:.3f}/{ph:.3f}/{pr:.3f}/{pc}{flag}")

good = [(s, v, c) for s, v, c in rows if None not in (v["llm"], v["hold"], v["rule"])]
if good:
    dh = [v["llm"] - v["hold"] for _, v, _ in good]
    dr = [v["llm"] - v["rule"] for _, v, _ in good]
    print(f"\n  primary   llm_minus_hold mean = {st.mean(dh):+.3f}  "
          f"paper {PAPER_PRIMARY[0]:+.3f}   positive in {sum(1 for x in dh if x > 0)}/{len(dh)}")
    print(f"  secondary llm_minus_rule mean = {st.mean(dr):+.3f}  "
          f"paper {PAPER_SECONDARY:+.3f}")
print(f"  cell mismatches: {bad}/10")

ap = BASE / "analysis.json"
if ap.exists():
    a = json.loads(ap.read_text(encoding="utf-8"))
    res = a.get("results", {})
    print(f"\n  batch analysis.json says:")
    for k, v in res.items():
        if isinstance(v, dict):
            print(f"    {k}: mean={v.get('mean')} ci={v.get('ci') or v.get('ci95')} "
                  f"pos/zero/neg={v.get('n_pos')}/{v.get('n_zero')}/{v.get('n_neg')}")
        else:
            print(f"    {k}: {v}")

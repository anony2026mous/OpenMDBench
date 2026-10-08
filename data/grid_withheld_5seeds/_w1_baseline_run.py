"""Re-run the single-architecture baselines under ONE policy identity.

Two problems this solves:

1. The archived `rl` episodes mix several checkpoints (`theta_rl_legacy2`,
   `theta_rl_main5`, `theta_rl_main4`, ...).  Averaging across them yields a number
   belonging to no actual policy, and IE-08 has no archived `rl` reading at all.
   Running the baseline here fixes the identity and fills the gap.

2. The archived episodes were produced over several days with varying scaffolding.
   Re-running them with the exact same launcher, seed set, resolution and reporting
   as the LLM arms puts both sides on a bit-identical footing, which is what the
   claim table needs.

`rl` is cheap (0.32 s/tick, no LLM call), so this runs alongside the LLM grid
without competing for the endpoint.  `rule-rule` is deterministic and already
matches the archive bit-for-bit (verified by the A/B code gate), so it is run here
only for the cells the archive does not cover.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
PY = Path(r"C:\Code\source-code\source_codes\.venv\Scripts\python.exe")
RUNS = EVAL / "_w1_runs"
THETA_RL = RUNS / "rl" / "theta_rl_legacy2.npz"

ENV = dict(os.environ)
ENV.update({
    "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
    "PYTHONPATH": str(ROOT), "OPENMDBENCH_ROOT": str(ROOT),
    "MPLCONFIGDIR": r"C:\Code\source-code\.mplcache",
})

IE = ["IE-01-SINGLE-TARGET", "IE-02-DUAL-THREAT", "IE-03-SURFACE-RAID",
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


def valid(p: Path, theta_name: str | None) -> tuple[bool, str]:
    if not p.exists():
        return False, "absent"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return False, f"unreadable ({exc})"
    card = d.get("strategy_scorecard") or {}
    if int(d.get("ticks_run") or 0) <= 0:
        return False, "ticks=0"
    if (card.get("terminal") or {}).get("outcome") in (None, "undecided"):
        return False, "no terminal outcome"
    if d.get("aborted"):
        return False, "aborted"
    raw = card.get("defender_score")
    rc = recomp(card)
    if raw is None or rc is None or abs(float(raw) - rc) > 5e-4:
        return False, "scorecard not reproducible"
    if theta_name:
        de = d.get("defender") or {}
        found = ""
        for blk in ("planner", "executor"):
            b = de.get(blk)
            if isinstance(b, dict) and b.get("theta"):
                found = Path(str(b["theta"])).name
                break
        if found != theta_name:
            return False, f"policy={found or '?'} (want {theta_name})"
    return True, f"ticks={d.get('ticks_run')} score={raw}"


def out_path(planner: str, scen: str, tag: str, seed: int) -> Path:
    suffix = "" if seed == 7 else f"_s{seed}"
    return RUNS / f"ie_{planner.replace('-', '')}_{scen.lower()}_{tag}{suffix}.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--planner", default="rl", choices=("rl", "rule"))
    ap.add_argument("--tag", default="base")
    ap.add_argument("--seeds", type=int, nargs="*", default=[7, 11, 13])
    ap.add_argument("--scenarios", nargs="*", default=None)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()

    scenarios = args.scenarios or IE
    theta_name = THETA_RL.name if args.planner == "rl" else None
    if args.planner == "rl" and not THETA_RL.is_file():
        print(f"ABORT: theta missing at {THETA_RL}")
        return 2

    print("=" * 96)
    print(f"BASELINE RUN   planner={args.planner}  tag={args.tag}  "
          f"seeds={args.seeds}  policy={theta_name or 'deterministic rule'}")
    print("=" * 96)

    todo = []
    for scen in scenarios:
        for seed in args.seeds:
            p = out_path(args.planner, scen, args.tag, seed)
            ok, why = valid(p, theta_name)
            if not ok:
                todo.append((scen, seed, why))
    print(f"  cells needed: {len(todo)} / {len(scenarios) * len(args.seeds)}")
    if not todo:
        print("  nothing to do")
        return 0

    import concurrent.futures as cf
    import _w1_ie_sweep as sweep

    def attempt(scen: str, seed: int):
        kw = dict(wall_limit=7200, hard_timeout=7800, step_timeout=180.0)
        if args.planner == "rl":
            kw.update(rl_theta=str(THETA_RL), rl_stochastic=True,
                      decision_interval=5, rl_speed_source="legacy_tags")
        for n in range(args.retries + 1):
            try:
                _, ok, detail = sweep.run_one(args.planner, scen, args.tag, seed, **kw)
            except Exception as exc:  # noqa: BLE001
                ok, detail = False, f"exception {type(exc).__name__}: {exc}"
            if ok:
                good, why = valid(out_path(args.planner, scen, args.tag, seed), theta_name)
                if good:
                    return scen, seed, True, f"{detail} (try {n + 1})"
                ok, detail = False, f"artifact rejected: {why}"
            if n < args.retries:
                time.sleep(5)
        return scen, seed, False, detail

    t0 = time.time()
    fails = []
    with cf.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futs = {pool.submit(attempt, s, sd): (s, sd) for s, sd, _ in todo}
        n = 0
        for fut in cf.as_completed(futs):
            scen, seed, ok, detail = fut.result()
            n += 1
            print(f"  [{n:>3}/{len(todo)}] [{'ok  ' if ok else 'FAIL'}] "
                  f"s{seed:<3} {scen:<28} {detail}", flush=True)
            if not ok:
                fails.append((scen, seed, detail))

    print(f"\n  {len(todo) - len(fails)}/{len(todo)} ok   "
          f"wall={time.time() - t0:.0f}s")
    if fails:
        for scen, seed, detail in fails:
            print(f"    FAILED s{seed} {scen}: {detail[:140]}")

    print("\n--- coverage after run ---")
    for scen in scenarios:
        row = f"  {scen:<28}"
        for seed in args.seeds:
            ok, _ = valid(out_path(args.planner, scen, args.tag, seed), theta_name)
            row += f"{('ok' if ok else 'MISSING'):>10}"
        print(row)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""P1 + P2 driver: fill the 3-arm x 14-scenario x 3-seed grid, withheld口径.

Why one driver instead of separate P1/P2 batches: the grid is the same object at
different densities.  Running "seed 7 for all scenarios, then seeds 11/13" as two
independent batches re-derives the same skip decisions twice and risks a second
tag-collision accident.  Here every cell has exactly one canonical filename and
one validity test, so P1 is simply "the seed-7 slice of the grid" and P2 is the
rest.  Re-running the driver is idempotent.

Concurrency: a thread pool of N, each slot running one episode subprocess.
The LLM endpoint is the shared bottleneck; 6 is the measured-safe ceiling
(9 previously tripped `step_timeout`), and `--step-timeout 180` is the valve.

Valid == run_episode wrote a report AND that report is a real episode:
  ticks_run > 0, terminal.outcome decided, no `aborted`, and (for LLM arms)
  `defender.briefing` == the requested口径.  A stale or contaminated file is
  never accepted as a skip.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT")
            or (EVAL.parents[1] / "source-code" / "source_codes"))
os.environ.setdefault("OPENMDBENCH_ROOT", str(ROOT))
sys.path.insert(0, str(EVAL))

import _w1_ie_sweep as sweep  # noqa: E402

RUNS = EVAL / "_w1_runs"
STATE = RUNS / "_grid_state.json"
LOCK = threading.Lock()

SCEN = list(sweep.IE_SET)
ARMS = ["llm", "llm-rl", "pure-llm"]
ARM_LABEL = {"llm": "llm-rule", "llm-rl": "llm-rl", "pure-llm": "pure-llm"}
THETA = str(RUNS / "rl" / "theta_arm5_llm_reward_v9.npz")

ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="n3")
ap.add_argument("--seeds", type=int, nargs="*", default=[7, 11, 13])
ap.add_argument("--arms", nargs="*", default=ARMS, choices=ARMS)
ap.add_argument("--scenarios", nargs="*", default=None)
ap.add_argument("--jobs", type=int, default=6)
ap.add_argument("--briefing", default="withheld", choices=("withheld", "declared"))
ap.add_argument("--retries", type=int, default=2)
ap.add_argument("--wall-limit", type=int, default=7200)
ap.add_argument("--episode-timeout", type=int, default=7800)
ap.add_argument("--step-timeout", type=float, default=180.0)
ap.add_argument("--dry-run", action="store_true",
                help="only report which cells are missing/valid")
ap.add_argument("--plan", action="store_true",
                help="print the cell plan and exit")
args = ap.parse_args()

SCENARIOS = args.scenarios or SCEN


def out_path(arm: str, scenario: str, seed: int) -> Path:
    suffix = "" if seed == 7 else f"_s{seed}"
    return RUNS / f"ie_{arm.replace('-', '')}_{scenario.lower()}_{args.tag}{suffix}.json"


def valid(p: Path) -> tuple[bool, str]:
    """Is an existing report a usable datapoint for this口径?"""
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
        return False, f"aborted: {str(d['aborted'])[:80]}"
    if card.get("defender_score") is None or card.get("scored_weight") is None:
        return False, "no scored defender_score"
    de = d.get("defender") or {}
    # The口径 lives in TWO places depending on the arm, and reading only one of
    # them silently reports "no provenance" for a perfectly tagged episode:
    #   pure-llm  -> defender.briefing            (the agent IS the planner)
    #   llm / llm-rl -> defender.planner.briefing (planner stats block)
    got = None
    if isinstance(de, dict):
        if isinstance(de.get("briefing"), str):
            got = de["briefing"]
        pl = de.get("planner")
        if got is None and isinstance(pl, dict) and isinstance(pl.get("briefing"), str):
            got = pl["briefing"]
    if got is not None and got != args.briefing:
        return False, f"briefing={got} (want {args.briefing})"
    return True, f"ticks={d.get('ticks_run')} score={card.get('defender_score')}"


cells = [(a, s, sd) for a in args.arms for sd in args.seeds for s in SCENARIOS]
todo, done = [], []
for a, s, sd in cells:
    p = out_path(a, s, sd)
    ok, why = valid(p)
    (done if ok else todo).append((a, s, sd, why))

print("=" * 96)
print(f"GRID  tag={args.tag}  arms={len(args.arms)}  seeds={args.seeds}  "
      f"scenarios={len(SCENARIOS)}  cells={len(cells)}  jobs={args.jobs}  "
      f"briefing={args.briefing}")
print("=" * 96)
print(f"  already valid : {len(done)}")
print(f"  to run        : {len(todo)}")
if args.plan or args.dry_run:
    for a, s, sd, why in todo:
        print(f"    RUN   {ARM_LABEL[a]:<9} seed={sd:<3} {s:<28} ({why})")
    for a, s, sd, why in done:
        print(f"    have  {ARM_LABEL[a]:<9} seed={sd:<3} {s:<28} ({why})")
    raise SystemExit(0)
if not todo:
    print("  nothing to do")
    raise SystemExit(0)

state = {}
if STATE.exists():
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        state = {}


def key(a, s, sd):
    return f"{a}|{s}|{sd}"


def attempt(a: str, s: str, sd: int) -> tuple[str, str, bool, str, float]:
    t0 = time.time()
    planner = a
    kw = dict(wall_limit=args.wall_limit, hard_timeout=args.episode_timeout,
              step_timeout=args.step_timeout, llm_briefing=args.briefing)
    if planner == "pure-llm":
        kw["pure_llm_envelope"] = "executor"
    if planner == "llm-rl":
        kw.update(rl_theta=THETA, rl_stochastic=True, decision_interval=5,
                  rl_speed_source="legacy_tags")
    for n in range(args.retries + 1):
        try:
            _, ok, detail = sweep.run_one(planner, s, args.tag, sd, **kw)
        except Exception as exc:  # noqa: BLE001
            ok, detail = False, f"exception: {type(exc).__name__}: {exc}"
        if ok:
            # re-validate the artifact itself: run_one trusts the report, but the
            #口径 field is ours to enforce.
            good, why = valid(out_path(a, s, sd))
            if good:
                return a, s, True, f"{detail} ({time.time() - t0:.0f}s, try {n + 1})", time.time() - t0
            ok, detail = False, f"artifact rejected: {why}"
        if n < args.retries:
            time.sleep(10.0 * (n + 1))
    return a, s, False, detail, time.time() - t0


t0 = time.time()
results = []
done_n = 0
total = len(todo)
print(f"\nlaunching {total} episodes at {args.jobs}-way concurrency ...\n", flush=True)
with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
    futs = {pool.submit(attempt, a, s, sd): (a, s, sd) for a, s, sd, _why in todo}
    for fut in as_completed(futs):
        a, s, ok, detail, el = fut.result()
        sd = futs[fut][2]
        with LOCK:
            done_n += 1
            mark = "ok  " if ok else "FAIL"
            print(f"  [{done_n:>3}/{total}] [{mark}] {ARM_LABEL[a]:<9} s{sd:<3} "
                  f"{s:<28} {detail}", flush=True)
            state[key(a, s, sd)] = {"ok": ok, "detail": detail,
                                    "elapsed_s": round(el, 1),
                                    "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
            STATE.write_text(json.dumps(state, indent=1, ensure_ascii=False),
                             encoding="utf-8")
            results.append((a, s, sd, ok))

ok_n = sum(1 for *_x, ok in results if ok)
print(f"\n  {ok_n}/{total} episodes ok   wall={time.time() - t0:.0f}s "
      f"({(time.time() - t0) / 60:.1f} min)")

# final coverage table
print("\n--- coverage after this run ---")
hdr = f"  {'scenario':<28}" + "".join(f"{ARM_LABEL[a]:>11}" for a in args.arms)
for sd in args.seeds:
    print(f"\n  seed {sd}")
    print(hdr)
    for s in SCENARIOS:
        row = f"  {s:<28}"
        for a in args.arms:
            good, why = valid(out_path(a, s, sd))
            row += f"{('ok' if good else 'MISSING'):>11}"
        print(row)

fails = [(a, s, sd) for a, s, sd, ok in results if not ok]
if fails:
    print("\n--- failures (re-run the driver to retry; state is persisted) ---")
    for a, s, sd in fails:
        print(f"    {ARM_LABEL[a]:<9} seed={sd:<3} {s:<28} {state[key(a, s, sd)]['detail'][:150]}")
raise SystemExit(1 if fails else 0)

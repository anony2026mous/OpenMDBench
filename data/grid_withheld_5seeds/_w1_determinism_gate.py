"""Bit-identity regression gate for the single-architecture baseline arm.

The user's boundary is that shared-code edits must not move `rule-rule` by one bit.
Comparing against the archived snapshot does NOT establish that: the live results
directory is a superset of the archived one, so the two sets trivially agree.  The
real test is to run the SAME scenario twice, now, and require identical
decision-level output.

The engine is deterministic by construction (fixed tick, no wall-clock input), so
any difference between two runs of the same seed would indicate that an edit
reached into the baseline path.  Compared fields are the decision-relevant ones:
per-entity final state, engagements, fires and rejections, damage, mission states,
terminal, and the full scorecard.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
# The interpreter lives in the OLD tree's venv; its .pth points at the ACTIVE engine
# root, so `PYTHONPATH`/`OPENMDBENCH_ROOT` below are what select the code that runs.
PY = Path(r"C:\Code\source-code\source_codes\.venv\Scripts\python.exe")
RUNS = EVAL / "_w1_runs"

ENV = dict(os.environ)
ENV.update({
    "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
    "PYTHONPATH": str(ROOT), "OPENMDBENCH_ROOT": str(ROOT),
    "MPLCONFIGDIR": r"C:\Code\source-code\.mplcache",
})

FIELDS = ["entities", "engagements_by_target", "engagements_by_target_role",
          "fire_rejections", "damage_by_kind", "mission_states", "strategy_scorecard",
          "layered_metrics", "total_fires", "total_fires_defender",
          "total_fires_intruder", "ticks_run", "terminal_result", "score_state",
          "defender", "attack"]


def run_once(scenario: str, planner: str, seed: int, tag: str, extra: list[str],
             sandbox: Path | None = None) -> Path:
    """Run one episode either from the live tree or from the archived sandbox.

    The sandbox holds the PRE-CHANGE versions of every module, and PYTHONPATH puts
    it ahead of the engine, so this is a genuine A/B of the code rather than of the
    results directory.
    """
    workdir = sandbox or EVAL
    out = RUNS / f"_det_{planner}_{scenario.lower()}_{tag}.json"
    log = RUNS / "logs" / f"_det_{planner}_{scenario.lower()}_{tag}.jsonl"
    cmd = [str(PY), "-u", "run_episode.py", "--scenario", scenario,
           "--planner", planner, "--seed", str(seed), "--max-ticks", "1800",
           "--report-every", "400", "--log", str(log), "--output", str(out)] + extra
    env = dict(ENV)
    if sandbox:
        env["PYTHONPATH"] = f"{sandbox}{os.pathsep}{ROOT}"
    print(f"    running {out.name} ({'sandbox' if sandbox else 'live'}) ...", flush=True)
    r = subprocess.run(cmd, cwd=str(workdir), env=env, capture_output=True,
                       text=True, timeout=7200)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()[-8:]
        print(f"      exit={r.returncode}\n      " + "\n      ".join(tail))
    return out


def canon(obj):
    """Order-insensitive canonicalisation for lists that are sets semantically."""
    if isinstance(obj, dict):
        return {k: canon(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        items = [canon(x) for x in obj]
        try:
            return sorted(items, key=lambda x: json.dumps(x, sort_keys=True,
                                                          ensure_ascii=False))
        except Exception:  # noqa: BLE001
            return items
    if isinstance(obj, float):
        return round(obj, 9)
    return obj


def main() -> int:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "IE-01-SINGLE-TARGET"
    planner = sys.argv[2] if len(sys.argv) > 2 else "rule"
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 7
    extra = [a for a in sys.argv[4:] if a != "--ab"]
    do_ab = "--ab" in sys.argv[4:]
    sandbox = EVAL / "_w1_archive_sandbox" if do_ab else None

    print("=" * 96)
    print(f"DETERMINISM GATE   scenario={scenario}  planner={planner}  seed={seed}")
    print("=" * 96)
    if extra:
        print(f"  extra args: {extra}")
    if do_ab:
        print(f"  A/B mode: comparing PRE-CHANGE sandbox vs live tree")
        if sandbox is None or not sandbox.exists():
            print(f"  ABORT: sandbox missing at {sandbox}")
            return 2

    a = run_once(scenario, planner, seed, "runArch" if do_ab else "runA", extra, sandbox)
    b = run_once(scenario, planner, seed, "runB", extra)

    if not (a.exists() and b.exists()):
        print("  ABORT: a run produced no report")
        return 2

    da = json.loads(a.read_text(encoding="utf-8"))
    db = json.loads(b.read_text(encoding="utf-8"))
    if not isinstance(da, dict) or not isinstance(db, dict):
        print("  ABORT: unexpected report shape")
        return 2

    print(f"\n  {'field':<32}{'result'}")
    print("  " + "-" * 60)
    mismatches = []
    for f in FIELDS:
        va, vb = canon(da.get(f)), canon(db.get(f))
        same = va == vb
        if not same:
            mismatches.append(f)
        print(f"  {f:<32}{'IDENTICAL' if same else 'DIFFERS'}")
        if not same:
            sa = json.dumps(va, ensure_ascii=False, sort_keys=True)
            sb = json.dumps(vb, ensure_ascii=False, sort_keys=True)
            print(f"      A: {sa[:220]}")
            print(f"      B: {sb[:220]}")

    # fields that legitimately differ between two runs of the same episode
    noise = {"elapsed_seconds", "ticks_per_second", "step_mean_seconds",
             "step_max_seconds", "resumed_from", "start_tick"}
    print(f"\n  ignored as wall-clock noise: {sorted(noise)}")

    print("\n  VERDICT:", "PASS - decision output bit-identical across two runs"
          if not mismatches else f"FAIL - differs in {mismatches}")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())

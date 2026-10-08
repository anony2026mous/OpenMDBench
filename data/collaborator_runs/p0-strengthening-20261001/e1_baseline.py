"""E1 preflight: independent-seed calibration anchor on UNMODIFIED scenarios.

This does not manipulate headroom and must not be called the full E1 experiment.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import subprocess
import sys
import time
from common import read, write, digest, estimate


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workers", type=int, default=10)
    a = p.parse_args()
    engine = a.repo / "openmd/source-code/source_codes"
    runner = a.repo / "openmd/code/eval/run_episode.py"
    a.output.mkdir(parents=True, exist_ok=True)
    scenes = {"IE-05-MULTI-AXIS": "ie_05_multi_axis", "IE-09-STAGGERED-WAVES": "ie_09_staggered_waves"}
    files = [*engine.glob("openmdbench/**/*.py"), *engine.glob("catalog/**/*.*"),
             *(a.repo / "openmd/code/eval").glob("*.py")]
    for slug in scenes.values():
        files += list((engine / "scenarios/formal" / slug).glob("*.yaml"))
    before = {str(f.relative_to(a.repo)): digest(f) for f in sorted(files) if f.is_file()}
    manifest = {"schema": "p0-e1-unmodified-baseline@1", "source_hashes": before,
                "seeds": list(range(1101, 1111)), "scenarios": list(scenes),
                "planner": "rule", "max_ticks": 1800, "plan_interval": 10,
                "purpose": "Calibration anchor only; no headroom treatment or hybrid comparison",
                "prohibited_claim": "Not full E1, not best-pure selection, not a causal headroom test"}
    if (a.output / "manifest.json").exists() and read(a.output / "manifest.json") != manifest:
        raise ValueError("Resume manifest mismatch")
    write(a.output / "manifest.json", manifest)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg", MPLCONFIGDIR=str(a.output / "mpl"),
               OPENMDBENCH_ROOT=str(engine))
    def run(scene, seed):
        folder = a.output / scene / f"seed-{seed}"
        path = folder / "report.json"
        if path.exists() and read(path).get("aborted") is None:
            return {"scenario": scene, "seed": seed, "report": str(path), "resumed": True, "code": 0}
        folder.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-B", str(runner), "--scenario", scene, "--planner", "rule",
               "--seed", str(seed), "--max-ticks", "1800", "--plan-interval", "10",
               "--llm-briefing", "withheld", "--output", str(path),
               "--log", str(folder / "episode.jsonl"), "--checkpoint-dir", str(folder / "checkpoints")]
        start = time.monotonic()
        with (folder / "stdout.log").open("w") as log:
            done = subprocess.run(cmd, env=env, cwd=folder, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        return {"scenario": scene, "seed": seed, "report": str(path), "code": done.returncode,
                "elapsed_seconds": time.monotonic()-start, "command": cmd}
    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(run, scene, seed) for scene in scenes for seed in manifest["seeds"]]
        for f in as_completed(futures):
            row = f.result()
            rows.append(row)
            write(a.output / "progress.json", rows)
            print(__import__('json').dumps(row), flush=True)
    after = {name: digest(a.repo / name) for name in before}
    write(a.output / "source_integrity.json", {"unchanged": before == after, "after": after})
    summary = {"design": manifest["purpose"], "records": rows, "engine_and_scenarios_unchanged": before == after,
               "headroom_tiers_created": False, "full_E1_complete": False}
    write(a.output / "summary.json", summary)
    if before != after or any(r["code"] or not Path(r["report"]).exists() or read(r["report"]).get("aborted") for r in rows):
        raise RuntimeError("Baseline engineering gate failed; inspect per-episode logs")


if __name__ == "__main__":
    main()

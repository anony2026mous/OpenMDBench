"""Resume-safe P0 orchestration; engine and scenario files are never edited."""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess
import sys
import time
from common import read, write


def main():
    root = Path(__file__).resolve().parent
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               CUDA_VISIBLE_DEVICES="", PYTHONDONTWRITEBYTECODE="1", MPLBACKEND="Agg",
               MPLCONFIGDIR=str(root / "mpl"))
    jobs = ([(s, v) for s in range(601, 611) for v in ["llm_original", "rule_planner"]]
            + [(s, v) for s in range(501, 511) for v in ["rule-rule", "rule-rl", "rl"]])
    def replay(seed, variant):
        folder = root / "frames" / f"s{seed}-{variant}"
        previous = list((root / "frames").glob(f"s{seed}-{variant}*/audit.json"))
        if any(read(p).get("eligible") for p in previous):
            return {"seed": seed, "variant": variant, "code": 0, "resumed": True}
        # Failed attempts retained; create numbered independent attempts.
        if folder.exists():
            folder = root / "frames" / f"s{seed}-{variant}-attempt{time.time_ns()}"
        command = [sys.executable, "-B", str(root / "e3_collect.py"),
                   "--source", str(root / "archive-source"), "--toolkit", str(root / "archive-toolkit"),
                   "--checkpoint", str(root / "assets/mappo_medium_s42_best.pt"),
                   "--campaign", str(root / ("inputs/P1__six_arm__s501-510__main__v1" if seed < 600 else "inputs/P3a__llm_goal_causal__s601-610__confirm__v1")),
                   "--seed", str(seed), "--variant", variant, "--output", str(folder)]
        log = root / "logs" / f"s{seed}-{variant}-{time.time_ns()}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w") as f:
            r = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=600)
        return {"seed": seed, "variant": variant, "code": r.returncode, "log": str(log)}
    completed = []
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [pool.submit(replay, s, v) for s, v in jobs]
        for f in as_completed(futures):
            row = f.result()
            completed.append(row)
            print(json.dumps(row), flush=True)
            write(root / "collection_progress.json", completed)
    write(root / "collection_summary.json", completed)
    if any(r["code"] for r in completed):
        raise RuntimeError("One or more exact replays failed; review before classification")
    classify = [sys.executable, "-B", str(root / "e3_classify.py"),
                "--frames", str(root / "frames"), "--output", str(root / "results/E3-expanded"),
                "--endpoints", "http://127.0.0.1:8101/v1", "http://127.0.0.1:8102/v1", "--workers", "16"]
    r = subprocess.run(classify, env=env)
    if r.returncode:
        raise RuntimeError("E3 classification failed; dataset audit retained")


if __name__ == "__main__":
    main()

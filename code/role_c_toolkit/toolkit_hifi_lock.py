"""Freeze a fresh 6.0 Role-C campaign; never runs an episode."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import p0_6_audit as audit

SCENES = audit.SCENARIOS
ARMS = ("rule", "llm", "rule-rl", "llm-rl", "rl", "pure-llm")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--scenario", action="append", choices=SCENES, required=True)
    p.add_argument("--seed", action="append", type=int, required=True)
    p.add_argument("--goal-granularity", choices=("weak", "medium", "strong"), default="strong")
    p.add_argument("--base-url", default="http://172.18.116.170:8000/v1")
    p.add_argument("--model", default="Qwen3.8-27B")
    args = p.parse_args()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        raise FileExistsError(f"New or empty output directory required: {out}")
    if any(seed < 0 for seed in args.seed):
        p.error("Seeds must be nonnegative")
    out.mkdir(parents=True, exist_ok=True)
    provenance = audit.freeze(out)
    extra = (audit.EVAL / "_gen_ie_set_ext.py",
             audit.ENGINE / "openmdbench" / "world" / "factory_v2.py")
    provenance["extra_files_sha256"] = {
        str(path.relative_to(audit.PROJECT)).replace("\\", "/"): audit.sha256(path)
        for path in extra
    }
    provenance["llm_configuration"]["base_url"] = args.base_url.rstrip("/")
    provenance["llm_configuration"]["model"] = args.model
    audit.save(out / "provenance.json", provenance)
    config = {
        "schema": "role-c-toolkit-hifi@1", "scenarios": list(dict.fromkeys(args.scenario)),
        "seeds": list(dict.fromkeys(args.seed)), "arms": list(ARMS),
        "goal_granularity": args.goal_granularity, "base_url": args.base_url.rstrip("/"),
        "model": args.model, "plan_interval": 10, "decision_interval": 5,
        "max_ticks": 1800, "llm_max_tokens": 1024,
        "note": "This manifest fixes the design. Run selected arms with --run-arm; never relabel prior seeds as holdout.",
    }
    audit.save(out / "toolkit_config.json", config)
    print(json.dumps({"output": str(out), "cells": len(config["scenarios"]) * len(config["seeds"]) * 6,
                      "goal_granularity": args.goal_granularity}, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Read-only readiness check for a frozen grid Role-C matrix.

This command never contacts an LLM endpoint or launches an episode.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from grid_rolec6 import digest, source_hashes
from grid_rolec6_analyze import analyze_matrix, read


def inspect_campaign(root: Path) -> dict:
    root = root.resolve()
    spec = read(root / "campaign.json")
    if spec.get("schema") != "grid-role-c-6-matrix@1":
        raise ValueError("Not a grid Role-C matrix")
    source = Path(spec["source"])
    checkpoint = Path(spec["checkpoint"]) if spec.get("checkpoint") else None
    runner = Path(__file__).with_name("grid_rolec6.py")
    try:
        source_match = source.is_dir() and source_hashes(source) == spec["source_hashes"]
    except (OSError, ValueError):
        source_match = False
    checks = {
        "source_hashes_match": source_match,
        "runner_hash_matches": digest(runner) == spec["implementation_sha256"],
        "checkpoint_hash_matches": (
            checkpoint.is_file() and digest(checkpoint) == spec["checkpoint_sha256"]
            if checkpoint else spec.get("checkpoint_sha256") is None),
    }
    audit = analyze_matrix(root)
    eligible = {(row["seed"], row["arm"]) for row in audit["cells"]}
    missing = {arm: [seed for seed in spec["seeds"] if (seed, arm) not in eligible]
               for arm in spec["arms"]}
    return {
        "campaign": str(root), "ready_to_resume": all(checks.values()),
        "checks": checks, "model": spec.get("model"), "base_url": spec.get("base_url"),
        "seed_count": len(spec["seeds"]), "arms": spec["arms"],
        "expected_cells": audit["expected"], "eligible_cells": audit["eligible"],
        "missing_seeds_by_arm": missing,
        "ineligible_attempts": [entry for entry in audit["attempts"]
                                if "path" in entry and not entry["eligible"]],
        "note": ("Read-only local check; does not verify live model availability or chat compatibility. "
                 "Keep existing v2 HTTP timeout/retry defaults (120 seconds, 2 retries)."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    args = parser.parse_args()
    report = inspect_campaign(args.campaign)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ready_to_resume"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

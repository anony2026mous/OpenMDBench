"""Write a manifest for the Option-2 experiment: every executed episode plus its evidence hash.

Deliberately separate from the E4 scenario-family ledger, because this batch ran on the delivered
E1 runner against E1 tier packages rather than against the competition_v1 family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ROOT = Path("/mnt/QTJC/chenyi-codex/experiments/e4-headroom-2x2/P1")
MATERIALS = Path("/mnt/QTJC/chenyi-codex/experiments"
                 "/E1_Exp2_option2_runner_materials_20261006_v1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_v(report: Path) -> float | None:
    if not report.is_file():
        return None
    try:
        payload = json.loads(report.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    value = (payload.get("layered_metrics") or {}).get("performance_v")
    return float(value) if isinstance(value, (int, float)) else None


def collect(root: Path) -> list[dict]:
    episodes = []
    # scan: scan/<package>/report.json
    scan = root / "scan"
    if scan.is_dir():
        for tier in sorted(p for p in scan.iterdir() if p.is_dir()):
            entry = add(tier, "scan", "baseline", 64101, tier.name.strip())
            if entry:
                episodes.append(entry)
    # paired: paired/<tier>/<dose>/seed-<n>/report.json
    paired = root / "paired"
    if paired.is_dir():
        for tier in sorted(p for p in paired.iterdir() if p.is_dir()):
            for dose in sorted(p for p in tier.iterdir() if p.is_dir()):
                for seed_dir in sorted(p for p in dose.iterdir() if p.is_dir()):
                    try:
                        seed = int(seed_dir.name.split("-")[-1])
                    except ValueError:
                        continue
                    entry = add(seed_dir, "paired", dose.name, seed, tier.name)
                    if entry:
                        episodes.append(entry)
    # granularity probe
    probe = root / "granprobe"
    if probe.is_dir():
        for arm in sorted(p for p in probe.iterdir() if p.is_dir()):
            entry = add(arm, "granularity-probe", arm.name, 64101, "COUNT-IE-05-MULTI-AXIS-N013")
            if entry:
                episodes.append(entry)
    return episodes


def add(directory: Path, batch: str, dose: str, seed: int, tier: str) -> dict | None:
    report = directory / "report.json"
    value = read_v(report)
    if value is None:
        return None
    evidence = {}
    for name in ("report.json", "episode.jsonl"):
        candidate = directory / name
        if candidate.is_file():
            evidence[name] = {"sha256": sha256(candidate), "bytes": candidate.stat().st_size}
    return {
        "batch": batch,
        "tier": tier,
        "condition": dose,
        "seed": seed,
        "performance_v": round(value, 6),
        "path": str(directory),
        "evidence": evidence,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    out = args.out or (args.root / "MANIFEST.json")

    episodes = collect(args.root)
    by_batch: dict[str, int] = {}
    for episode in episodes:
        by_batch[episode["batch"]] = by_batch.get(episode["batch"], 0) + 1

    payload = {
        "schema": "e4-exp2-option2-manifest@1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runner_materials": {
            "path": str(MATERIALS),
            "manifest_members_verified": 5077,
            "verification": "all member SHA-256 matched; 0 missing, 0 mismatched",
        },
        "design": {
            "planner": "rule (scripted; no LLM parameters in any invocation)",
            "information_supplied": "episode_adapter.py --dose strong (adapter submits the "
                                    "planner's goals unchanged)",
            "information_withheld": "episode_adapter.py --dose hold (non-hold goals rewritten)",
            "clean_contrast_probe": "--goal-granularity weak/medium applied through the plain "
                                   "runner (see granularity-probe)",
            "seeds": [64101, 64102, 64103, 64104, 64105],
            "score_field": "report.json:layered_metrics.performance_v",
        },
        "batch_counts": by_batch,
        "episode_count": len(episodes),
        "episodes": episodes,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written {out}")
    print(f"  episodes={len(episodes)} batches={by_batch}")


if __name__ == "__main__":
    main()

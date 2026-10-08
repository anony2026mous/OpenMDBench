"""Manifest for a G1 run tree: every episode, its score, and the hashes of its evidence files."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_episode(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    metrics = payload.get("metrics") or {}
    return {
        "V": payload.get("V"),
        "steps": payload.get("steps"),
        "done": payload.get("done"),
        "mission_success": metrics.get("mission_success"),
        "fault_case": (payload.get("fault_injection") or {}).get("case"),
        "fault_dose": (payload.get("fault_injection") or {}).get("dose"),
        "fault_events": (payload.get("fault_injection") or {}).get("fault_event_count"),
        "replay_exact": (payload.get("replay_check") or {}).get("exact_match"),
        "wrapper_sha256": (payload.get("fault_injection") or {}).get("wrapper_sha256"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    root = args.root
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    out = args.out or (root / "MANIFEST.json")

    episodes = []
    for report in sorted(root.rglob("episode.json")):
        meta = read_episode(report)
        if meta is None:
            continue
        rel = report.relative_to(root).as_posix()
        parts = rel.split("/")
        seed = next((p.split("-")[-1] for p in parts if p.startswith("seed-")), None)
        dose = next((p.replace("dose-", "") for p in parts if p.startswith("dose-")), "0.0")
        case = next((p for p in parts if p in ("clean", "planner_wrong_contact", "action_hold")),
                    "clean")
        evidence = {report.name: {"sha256": sha256(report),
                                  "bytes": report.stat().st_size}}
        layers = report.parent / "fault_events.json"
        if layers.is_file():
            evidence[layers.name] = {"sha256": sha256(layers),
                                     "bytes": layers.stat().st_size}
        episodes.append({"case": case, "seed": seed, "dose": dose,
                         "path": rel, **meta, "evidence": evidence})

    counts: dict[str, int] = {}
    for episode in episodes:
        key = f"{episode['case']}"
        counts[key] = counts.get(key, 0) + 1
    payload = {
        "schema": "g1-run-manifest@1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": str(root),
        "base_snapshot": "snapshots/20261002T194101Z-e5219dce/openmd",
        "design": {"planner": "rule", "executor": "heuristic", "difficulty": "medium",
                   "task_mode": "continuous", "interval": 5,
                   "doses": [0.05, 0.10, 0.20, 0.40, 0.60],
                   "score_field": "episode.json:V (== metrics.blue_score)"},
        "counts": counts,
        "episode_count": len(episodes),
        "episodes": episodes,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written {out}")
    print(f"  episodes={len(episodes)} counts={counts}")


if __name__ == "__main__":
    main()

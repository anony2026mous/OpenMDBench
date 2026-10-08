"""Read-only guard for pre-existing engine, catalogs and formal scenarios.

This freezes the local working tree, NOT Git HEAD or historical result validity.
Only an explicit first capture writes an artifact; verification never refreshes it.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path("artifacts/competition_four_categories/protected_inputs_baseline.json")
ANCHOR = Path("artifacts/competition_four_categories/engine_integrity_baseline.json")


def inventory(root: Path) -> dict[str, str]:
    paths = set((root / "openmdbench").rglob("*.py"))
    paths.update(p for p in (root / "scenarios/formal").rglob("*")
                 if p.is_file() and p.suffix in {".yaml", ".yml", ".json", ".md", ".py"})
    paths.update(p for p in (root / "catalog/v2").glob("*.yaml")
                 if p.name != "competition_four_categories.yaml")
    if not paths:
        raise ValueError("No protected inputs found; refusing an empty baseline")
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def capture(root: Path = ROOT) -> dict:
    path = root / BASELINE
    if path.exists():
        raise FileExistsError("Protected baseline already exists; never auto-refresh it")
    current = inventory(root)
    anchor_path = root / ANCHOR
    if anchor_path.exists():
        anchor = json.loads(anchor_path.read_text(encoding="utf-8-sig"))
        changed = [item["path"] for item in anchor["files"]
                   if current.get(item["path"]) != item["working_tree_sha256"]]
        if changed:
            raise ValueError(f"Original engine freeze changed: {changed}")
    payload = {"schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
               "scope": "current working tree, not historical-result certification",
               "files": current}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, indent=2) + "\n")
    return payload


def verify(root: Path = ROOT) -> dict:
    payload = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    expected = payload.get("files")
    if payload.get("schema_version") != 1 or not isinstance(expected, dict) or not expected:
        raise ValueError("Invalid protected-input baseline")
    actual = inventory(root)
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    missing = sorted(expected.keys() - actual.keys())
    added = sorted(actual.keys() - expected.keys())
    if changed or missing or added:
        raise ValueError(f"Protected inputs changed: modified={changed}, missing={missing}, added={added}")
    return {"status": "UNCHANGED", "file_count": len(actual),
            "baseline_sha256": hashlib.sha256((root / BASELINE).read_bytes()).hexdigest(),
            "captured_at": payload["captured_at"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="First capture only; existing baselines are never replaced")
    args = parser.parse_args()
    if args.capture:
        capture()
    print(json.dumps(verify(), indent=2))

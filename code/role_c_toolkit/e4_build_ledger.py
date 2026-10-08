"""Re-apply the ledger merges from the recorded analysis, so the ledger can be rebuilt.

The ledger is a derived artifact: it is regenerated from the inventory, the D1' table, the
binary D2 probe and the graded D2 measurement.  Editing it by hand (or re-running only one
merge on top of an older ledger) is what produced a mis-assigned row once, so this script
performs the whole chain in order.

Usage: python e4_build_ledger.py --artifacts <paper-E5-style artifacts dir>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def analysis_file(artifacts: Path, *names: str) -> Path | None:
    """First existing candidate, so a newer batch silently supersedes an older one."""
    for name in names:
        candidate = artifacts / "analysis" / name
        if candidate.is_file():
            return candidate
    return None


def run(*arguments: str) -> None:
    command = [sys.executable, str(HERE / "e4_scenario_family.py"), *arguments]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    print("$", " ".join(str(part) for part in arguments[1:3]), "->",
          (result.stdout or result.stderr).strip().splitlines()[-1] if (result.stdout or result.stderr) else "")
    if result.returncode != 0:
        raise SystemExit(f"merge failed: {result.stderr}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--grid-doc", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--design-root", type=Path, required=True)
    parser.add_argument("--d1-report", type=Path, required=True)
    parser.add_argument("--control-report", default="")
    args = parser.parse_args()
    artifacts = args.artifacts
    ledger = artifacts / "admission_ledger.json"
    run("inventory", "--source", str(args.source), "--output",
        str(artifacts / "scenario_inventory.json"), "--ledger-output", str(ledger),
        "--control-report", args.control_report, "--d1-report", str(args.d1_report),
        "--d1-source-label", "E10_HF_restricted-continuous_p02_20261003:results/analysis/a01/summary.json")
    run("d1prime-merge", "--ledger", str(ledger), "--table-json",
        str(artifacts / "d1prime_table.json"))
    binary = analysis_file(artifacts, "d2_headroom_final2.json", "d2_headroom_final.json",
                           "d2_headroom_postcal.json", "d2_headroom_5seed.json",
                           "d2_headroom.json")
    if binary:
        run("d2-merge", "--ledger", str(ledger), "--headroom", str(binary),
            "--evidence", "role_c_toolkit/artifacts/e4-scenario-family/analysis/" + binary.name)
    graded = analysis_file(artifacts, "d2_graded_final2.json", "d2_graded_final.json",
                           "d2_graded_postcal.json", "d2_graded_5seed.json", "d2_graded.json")
    if graded:
        run("d2-merge-graded", "--ledger", str(ledger), "--graded", str(graded),
            "--evidence", "role_c_toolkit/artifacts/e4-scenario-family/analysis/" + graded.name)
    run("report", "--ledger", str(ledger), "--output",
        str(artifacts / "appendix_A_scenario_family.md"))
    payload = json.loads(ledger.read_text(encoding="utf-8"))
    summary = {
        "scenarios": len(payload["scenarios"]),
        "d1prime_matched": payload.get("d1prime_applied", {}).get("matched"),
        "d2_matched": payload.get("d2_applied", {}).get("matched"),
        "d2_graded_matched": payload.get("d2_graded_applied", {}).get("matched"),
        "d2_graded_bands": payload.get("d2_graded_applied", {}).get("bands"),
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

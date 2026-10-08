"""Minimal probe: can this interpreter spawn the engine python with cwd=eval?"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Code\source-code\openmd\source-code\source_codes")
EVAL = Path(r"C:\Code\source-code\openmd\code\eval")
PY = ROOT / ".venv" / "Scripts" / "python.exe"

print("this interpreter :", sys.executable)
print("target python    :", PY, "exists=", PY.exists())
print("eval dir         :", EVAL, "exists=", EVAL.exists())

for label, exe in (("as Path", str(PY)), ("as str", str(PY))):
    for cwd in (str(EVAL), None):
        try:
            r = subprocess.run([exe, "-c", "print('child ok')"],
                               cwd=cwd, capture_output=True, text=True, timeout=120)
            print(f"  {label:<8} cwd={str(cwd):<45} rc={r.returncode} out={r.stdout.strip()!r}")
        except Exception as exc:  # noqa: BLE001
            print(f"  {label:<8} cwd={str(cwd):<45} RAISED {type(exc).__name__}: {exc}")

# and with the real relative script name
cmd = [str(PY), "-u", "run_episode.py", "--help"]
for cwd in (str(EVAL),):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=180)
        print(f"\n  run_episode --help rc={r.returncode}")
        print("  first lines:", (r.stdout or r.stderr).strip().splitlines()[:3])
    except Exception as exc:  # noqa: BLE001
        print(f"\n  run_episode --help RAISED {type(exc).__name__}: {exc}")

print("\n  env PYTHONPATH =", os.environ.get("PYTHONPATH"))
print("  env OPENMDBENCH_ROOT =", os.environ.get("OPENMDBENCH_ROOT"))

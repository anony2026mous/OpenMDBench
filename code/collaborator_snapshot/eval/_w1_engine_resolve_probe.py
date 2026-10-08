"""Probe which openmdbench tree the venv import resolves to (default vs PYTHONPATH)."""
import os
import sys

ACTIVE = r"C:\Code\source-code\openmd\source-code\source_codes"
STALE = r"C:\Code\source-code\source_codes"

print("PYTHONPATH =", os.environ.get("PYTHONPATH"))
print("OPENMDBENCH_ROOT =", os.environ.get("OPENMDBENCH_ROOT"))
print("cwd =", os.getcwd())
print("sys.path[:8] =")
for p in sys.path[:8]:
    print("   ", p)

try:
    import openmdbench

    loc = os.path.dirname(os.path.abspath(openmdbench.__file__))
    print("\nopenmdbench resolved ->", loc)
    if loc.lower().startswith(ACTIVE.lower()):
        print("RESULT: ACTIVE submodule engine")
    elif loc.lower().startswith(STALE.lower()):
        print("RESULT: *** STALE outer tree (wrong!) ***")
    else:
        print("RESULT: other")
    print("version:", getattr(openmdbench, "__version__", "n/a"))
except Exception as exc:  # noqa: BLE001
    print("\nimport failed:", type(exc).__name__, exc)

# does the active engine expose the declarative v2 modules the sweps need?
for mod in ("openmdbench.scenarios.declarative_v2", "openmdbench.sessions.lifecycle_v2"):
    try:
        __import__(mod)
        m = sys.modules[mod]
        print(f"OK   {mod} -> {os.path.abspath(m.__file__)}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {mod}: {type(exc).__name__}: {exc}")

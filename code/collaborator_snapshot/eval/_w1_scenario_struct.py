"""Dump the scenario document structure and locate the termination rules.

Written as a file because inline `-c` strings lose their quotes in this shell.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

FORMAL = Path(r"C:\Code\source-code\openmd\source-code\source_codes\scenarios\formal")
d = "ie_01_single_target" if len(sys.argv) < 2 else sys.argv[1]
doc = yaml.safe_load((FORMAL / d / "scenario.yaml").read_text(encoding="utf-8"))

print(f"top-level keys: {list(doc.keys())}")
sc = doc.get("scenario") or {}
print(f"\nscenario keys ({len(sc)}):")
for k, v in sc.items():
    if isinstance(v, dict):
        print(f"  {k:<26} dict keys={list(v.keys())[:14]}")
    elif isinstance(v, list):
        print(f"  {k:<26} list len={len(v)}")
        if v and isinstance(v[0], dict):
            print(f"      first item keys: {list(v[0].keys())[:14]}")
    else:
        print(f"  {k:<26} {v}")


def walk(node, path=""):
    """Yield every dict that looks like a rule (has id + condition/outcome)."""
    if isinstance(node, dict):
        if "id" in node and ("condition" in node or "outcome" in node):
            yield path, node
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


print("\n--- every rule-like node found ---")
for path, r in walk(doc):
    rid = str(r.get("id"))
    cond = r.get("condition") or {}
    out = r.get("outcome") or {}
    sel = cond.get("selector") or {}
    print(f"  {path}")
    print(f"    id={rid} priority={r.get('priority')} "
          f"terminal={out.get('terminal')} result={out.get('result')}")
    print(f"    operator={cond.get('operator')} params={cond.get('parameters')}")
    print(f"    selector tags={sel.get('tags')} lifecycles={sel.get('include_lifecycle')}")

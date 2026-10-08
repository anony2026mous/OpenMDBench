"""Ad-hoc structural dump of one arm report (keys + fire-related subtree)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))


def shape(node, depth=0, path=""):
    pad = "  " * depth
    if isinstance(node, dict):
        print(f"{pad}{path} dict({len(node)})")
        if depth < 3:
            for key, value in node.items():
                shape(value, depth + 1, str(key))
    elif isinstance(node, list):
        print(f"{pad}{path} list({len(node)})")
        if node and depth < 3:
            shape(node[0], depth + 1, "[0]")
    else:
        text = repr(node)
        print(f"{pad}{path} = {text[:110]}")


print("=== top level ===")
shape(report)
for key in report:
    if "fire" in key.lower() or "reject" in key.lower() or "engage" in key.lower():
        print(f"\n=== {key} ===")
        shape(report[key])

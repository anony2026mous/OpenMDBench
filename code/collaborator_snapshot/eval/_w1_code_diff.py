"""Compact hunk-level diff between an archived eval file and the live one.

Used to prove that every edit made during the口径 work is confined to the
intelligence channel. Only hunk headers plus a few context lines are printed, so a
large rewrite stays readable.
"""
from __future__ import annotations

import difflib
import os
import pathlib
import sys

SNAP = pathlib.Path(os.path.expanduser("~")) / "openmd_private_archive" / \
    "declared_briefing_snapshot_20260927_1419" / "code"
LIVE = pathlib.Path(r"C:\Code\source-code\openmd\code\eval")

for name in sys.argv[1:]:
    a = (SNAP / name).read_text(encoding="utf-8").splitlines()
    b = (LIVE / name).read_text(encoding="utf-8").splitlines()
    sm = difflib.SequenceMatcher(None, a, b)
    print("=" * 92)
    print(f"{name}   archived={len(a)} lines   live={len(b)} lines")
    print("=" * 92)
    n = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        n += 1
        print(f"\n  hunk {n}: {tag}  old[{i1}:{i2}] -> new[{j1}:{j2}]  "
              f"(-{i2 - i1} +{j2 - j1})")
        for x in a[i1:i2][:5]:
            print(f"      - {x.strip()[:150]}")
        if (i2 - i1) > 5:
            print(f"      - ... (+{i2 - i1 - 5} more removed)")
        for x in b[j1:j2][:5]:
            print(f"      + {x.strip()[:150]}")
        if (j2 - j1) > 5:
            print(f"      + ... (+{j2 - j1 - 5} more added)")
    print(f"\n  => {n} changed regions")

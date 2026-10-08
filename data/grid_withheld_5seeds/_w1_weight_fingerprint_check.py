"""Verify the released weight fingerprints against the values recorded in the docs."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs\rl"
DOC = r"C:\Code\source-code\openmd\code\eval\PAPER_READINESS_GAPS.md"

doc = open(DOC, encoding="utf-8").read()
# e.g. "v9 `b87e3020…`、v12 `26bfacb5…`"
rec = dict(re.findall(r"(v\d+)\s*`([0-9a-f]{8})", doc))
print("fingerprints recorded in PAPER_READINESS_GAPS.md:")
for k, v in sorted(rec.items()):
    print(f"   {k:<5} {v}")
print()

LABEL = {"reward_v9": "v9", "v10": "v10", "v11": "v11", "v12": "v12", "v13": "v13"}

print("actual files in the repo:")
ok = mismatch = unknown = 0
for p in sorted(glob.glob(os.path.join(RUNS, "theta_*.npz"))):
    n = os.path.basename(p)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    key = next((lab for pat, lab in LABEL.items() if pat in n), None)
    if key and key in rec:
        same = rec[key] == h[:8]
        mark = "MATCH" if same else f"MISMATCH (doc={rec[key]})"
        ok += same
        mismatch += (not same)
    else:
        mark = "(no recorded fingerprint)"
        unknown += 1
    print(f"  {n:<40} {h[:8]}  {mark}")

print()
print(f"match={ok} mismatch={mismatch} no-record={unknown}")

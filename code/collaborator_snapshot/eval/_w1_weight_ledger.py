"""Full fingerprint ledger + loadability check for every weight shipped in the repo."""
from __future__ import annotations

import glob
import hashlib
import json
import os

import numpy as np

RUNS = r"C:\Code\source-code\openmd\code\eval\_w1_runs\rl"

print("| weight | SHA-256 | arrays | params | role |")
print("|---|---|---|---|---|")
ROLE = {
    "theta_arm5_llm_reward_v9.npz": "hybrid B default (`--hybrid-ckpt`)",
    "theta_rl_legacy2.npz": "`rl` baseline (tag rlb2)",
    "theta_arm5_llm_full_ie03_v10.npz": "weight candidate v10",
    "theta_arm5_v11.npz": "weight candidate v11",
    "theta_arm5_v12.npz": "weight candidate v12 (IE-01 3/3 tail counterexample)",
    "theta_arm5_v13_ie08.npz": "weight candidate v13 (IE-01 control)",
}
total = 0
for p in sorted(glob.glob(os.path.join(RUNS, "theta_*.npz"))):
    n = os.path.basename(p)
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    total += os.path.getsize(p)
    try:
        d = np.load(p, allow_pickle=True)
        arrs = [k for k in d.keys()]
        params = sum(int(np.prod(d[k].shape)) for k in arrs if hasattr(d[k], "shape"))
        load = "ok"
    except Exception as exc:  # noqa: BLE001
        arrs, params, load = [], 0, f"FAIL {exc}"
    print(f"| `{n}` | `{h[:16]}…` | {len(arrs)} | {params:,} | {ROLE.get(n,'-')} ({load}) |")

print()
print(f"shipped weights: {len(glob.glob(os.path.join(RUNS, 'theta_*.npz')))} files, "
      f"{total / 2**20:.2f} MB")

# shape compatibility: all llm-rl candidates must share one architecture
print()
print("architecture compatibility across the llm-rl candidates:")
ref = None
for p in sorted(glob.glob(os.path.join(RUNS, "theta_arm5_*.npz"))):
    d = np.load(p, allow_pickle=True)
    sig = {k: d[k].shape for k in sorted(d.keys())}
    if ref is None:
        ref, refname = sig, os.path.basename(p)
        print(f"  reference = {refname} ({len(sig)} arrays)")
    else:
        same = sig == ref
        print(f"  {os.path.basename(p):<38} identical layout={same}")

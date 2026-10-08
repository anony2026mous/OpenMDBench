"""Warm-start equivalence check: with the new block zero, the grown checkpoint must
reproduce the source checkpoint's outputs exactly.

If it does not, "the policy changed after adding the assignment mask" would be
uninterpretable -- the change could be an initialisation artefact rather than the new
input being learned.

Usage: python _w1_test_warmstart_equivalence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_policy import load_theta, numpy_forward  # noqa: E402

OLD = HERE / "_w1_runs" / "rl" / "theta_arm5_v2.npz"
NEW = HERE / "_w1_runs" / "rl" / "theta_arm5_warm.npz"


def main() -> int:
    if not (OLD.is_file() and NEW.is_file()):
        print("checkpoints missing; run _w1_warmstart_theta.py first")
        return 2
    old, new = load_theta(OLD), load_theta(NEW)
    old_dim = int(old["trunk0.w"].shape[0])
    new_dim = int(new["trunk0.w"].shape[0])
    rng = np.random.default_rng(0)
    base = rng.normal(0.0, 0.3, size=old_dim).astype(np.float32)
    grown = np.concatenate([base, np.zeros(new_dim - old_dim, dtype=np.float32)])
    a = numpy_forward(old, base, 16, 21)
    b = numpy_forward(new, grown, 16, 21)
    ok = True
    for head in ("heading", "speed", "fire", "value"):
        delta = float(np.max(np.abs(np.asarray(a[head]) - np.asarray(b[head]))))
        same = delta < 1e-6
        ok = ok and same
        print(f"  {head:8} max|old-new| = {delta:.3e}  {'ok' if same else 'MISMATCH'}")
    print(f"  dimensions: {old_dim} -> {new_dim}")
    print("PASS: warm start is behaviour-identical while the new block is zero"
          if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

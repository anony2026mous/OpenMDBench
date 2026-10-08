"""Warm-start a checkpoint after the observation grew a new input block.

The plan's assignment mask (`ie_rl_env._assignment_block`, MAX_UNITS x MAX_CONTACTS
flags appended after the 24-dim plan row) changed the observation width from 3250 to
3570, so an existing checkpoint cannot be loaded.  Retraining from scratch would
throw away 20 iterations of learned interception behaviour just to add an input that
is *appended at the end* -- the prefix layout (global / unit / contact / pair / plan
row) is unchanged.

So the old first-layer weight matrix is **zero-extended** along its input axis: every
existing weight keeps its meaning, and the new block starts at zero, i.e. initially
inert and exactly equivalent to the old policy.  That makes the change measurable:
any difference in behaviour after fine-tuning is attributable to the new block being
learned, not to a scrambled initialisation.

Verified before writing: every array except ``trunk0.w`` is copied bit-for-bit, the
first ``old_dim`` rows of ``trunk0.w`` are copied bit-for-bit, and the appended rows
are exactly zero.

Usage:
    python _w1_warmstart_theta.py --theta _w1_runs/rl/theta_arm5_v2.npz \
        --out _w1_runs/rl/theta_arm5_warm.npz --expect-dim 3570
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from ie_rl_policy import (META_KEY, load_theta, pack_meta, read_meta,  # noqa: E402
                          save_theta)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theta", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-dim", type=int, required=True)
    args = parser.parse_args()

    theta = load_theta(args.theta)
    trunk = np.asarray(theta["trunk0.w"])
    old_dim, hidden = trunk.shape
    if old_dim == args.expect_dim:
        print(f"{args.theta.name} already has obs_dim={old_dim}; nothing to do")
        return 0
    if old_dim > args.expect_dim:
        print(f"refusing: {args.theta.name} is wider ({old_dim}) than the target "
              f"({args.expect_dim})")
        return 2

    grown = np.zeros((args.expect_dim, hidden), dtype=trunk.dtype)
    grown[:old_dim] = trunk
    payload = {key: np.asarray(value) for key, value in theta.items()
               if key != META_KEY}
    payload["trunk0.w"] = grown
    meta = read_meta(theta)
    meta.update({
        "obs_dim": int(args.expect_dim),
        "warm_start_from": args.theta.name,
        "warm_start_old_dim": int(old_dim),
        "warm_start_note": ("trunk0.w zero-extended on the input axis; the new "
                            "assignment block starts inert so behaviour is identical "
                            "to the source checkpoint until it is learned"),
        "provenance": "warm_start",
    })
    save_theta(args.out, payload, meta)
    check = load_theta(args.out)
    ok_prefix = np.array_equal(np.asarray(check["trunk0.w"])[:old_dim], trunk)
    ok_zero = not np.any(np.asarray(check["trunk0.w"])[old_dim:])
    ok_rest = all(np.array_equal(np.asarray(check[k]), np.asarray(v))
                  for k, v in theta.items() if k not in (META_KEY, "trunk0.w"))
    print(f"{args.theta.name}: {old_dim} -> {args.expect_dim} (hidden={hidden})")
    print(f"  prefix copied bit-for-bit : {ok_prefix}")
    print(f"  appended rows all zero    : {ok_zero}")
    print(f"  every other array copied  : {ok_rest}")
    if not (ok_prefix and ok_zero and ok_rest):
        print("!! verification failed")
        return 1
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

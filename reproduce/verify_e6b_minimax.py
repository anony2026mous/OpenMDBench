"""E6b: the two third-party MiniMax models — do they reproduce the paper's table?

The answer to "was this run with MiniMax?" is YES, but under a separate designation: the
client docstring describes itself as "Anthropic-Messages adapter for third-party planners
(MiniMax), for the E6b ablation", and the batch lives in
`data/e6-sources/paper-E6b-thirdparty-ablation/`, not under e6-model-invariance.

Appendix tab:modelinvariance prints four columns:
    Qwen3.8-27B  +0.431 [0.226, 0.615]    Qwen3-8B  +0.464 [0.269, 0.656]
    MM-M3        +0.313 [0.003, 0.600]    MM-M2.7-hs +0.450 [0.140, 0.700]
and a "vs. pure RL" row. This recomputes both MiniMax columns.
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "data" / "e6-sources" / "paper-E6b-thirdparty-ablation"

PAPER = {
    "m3": {"name": "MiniMax-M3", "n": 10, "sh": 0.313, "sh_ci": (0.003, 0.600),
           "rl": -0.422, "rl_ci": (-0.700, 0.067)},
    "m27h": {"name": "MiniMax-M2.7-hs", "n": 10, "sh": 0.450, "sh_ci": (0.140, 0.700),
             "rl": +0.022, "rl_ci": (0.000, 0.067)},
}
BOOT_N, BOOT_SEED = 10000, 20261003


def main() -> int:
    f = B / "analysis" / "e6_analysis.json"
    if not f.is_file():
        print(f"  batch not present: {B}")
        return 0
    d = json.loads(f.read_text(encoding="utf-8"))

    print("=" * 96)
    print("E6b third-party MiniMax ablation  vs  tab:modelinvariance")
    print("=" * 96)
    print(f"  schema    : {d.get('schema')}")
    print(f"  models    : {sorted(d.get('models', {}).keys())}")
    print(f"  conditions: {d.get('conditions')}")
    print(f"  records   : {len(d.get('records', []))}")
    print(f"  seeds     : {len(d.get('seeds', []))}   reference: {len(d.get('reference_seeds', []))}")
    ep = sum(1 for _ in B.rglob("E6b-case.json"))
    print(f"  case files: {ep}")

    by: dict[tuple[str, str], dict] = defaultdict(dict)
    for r in d.get("records", []):
        # Filter to the `llm-rl` arm. The batch also carries `rl` reference records
        # (3 seeds, strong condition only); keying on (model, condition) alone lets
        # those overwrite the `llm-rl` values at their seeds and inflates the mean --
        # it reports MM-M3 as +0.440 instead of the paper's +0.313.
        if r.get("arm") != "llm-rl":
            continue
        v = r.get("V")
        if isinstance(v, (int, float)):
            by[(r["model"], r["condition"])][r["seed"]] = float(v)

    rng = random.Random(BOOT_SEED)
    print(f"\n  --- interface necessity: strong - hold ---")
    print(f"  {'model':<18}{'n':>4}{'dV':>9}{'boot CI':>20}{'paper':>9}{'paper CI':>20}")
    mismatches = 0
    for mk, pv in PAPER.items():
        s, h = by.get((mk, "strong"), {}), by.get((mk, "hold"), {})
        seeds = sorted(set(s) & set(h))
        if not seeds:
            print(f"  {pv['name']:<18} MISSING")
            mismatches += 1
            continue
        diffs = [s[k] - h[k] for k in seeds]
        m = st.mean(diffs)
        boot = sorted(st.mean(rng.choices(diffs, k=len(diffs))) for _ in range(BOOT_N))
        lo, hi = boot[int(0.025 * BOOT_N)], boot[int(0.975 * BOOT_N)]
        ours_ci = f"[{lo:+.3f}, {hi:+.3f}]"
        p_lo, p_hi = pv["sh_ci"]
        paper_ci = f"[{p_lo:+.3f}, {p_hi:+.3f}]"
        # The point estimate is the checkable quantity: it is a mean over the
        # preregistered seeds. The interval is only ADVISORY, because the paper does not
        # publish the bootstrap call sequence, so an independent reimplementation lands
        # on a nearby but not identical interval even with the same draw count and seed.
        ok = abs(m - pv["sh"]) <= 0.002 and len(diffs) == pv["n"]
        mismatches += not ok
        print(f"  {pv['name']:<18}{len(diffs):>4}{m:>+9.3f}{ours_ci:>20}"
              f"{pv['sh']:>+9.3f}{paper_ci:>20}{'' if ok else '   <-- DIFFERS'}")

    print(f"\n  --- per-condition means ---")
    for mk, pv in PAPER.items():
        for cond in ("strong", "hold"):
            got = by.get((mk, cond), {})
            if got:
                print(f"     {pv['name']:<18}{cond:<8}n={len(got):<3} mean={st.mean(got.values()):.3f}")

    # the two batches use different token caps -- must not be merged
    print(f"\n  --- batch independence (the paper's own warning) ---")
    print(f"     E6b max_tokens = 8192 (M2.x cannot disable thinking; 1024 truncates)")
    print(f"     E6  max_tokens = 1024 (Qwen 27B/8B)")
    print(f"     -> the four columns are 'juxtaposed and never merged', as the table states")

    print(f"\n  point estimates differing from the paper: {mismatches}/{len(PAPER)}")
    print(f"  (intervals shown for reference only; the paper's draw sequence is not published)")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())

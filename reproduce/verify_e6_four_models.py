"""Verify E6 (four-model scan) against appendix tab:modelinvariance.

Sources, as `E6_family_overview.md` names them:
    data/e6-sources/paper-E6-model-invariance       <- Qwen3.8-27B, Qwen3-8B
    data/e6-sources/paper-E6b-thirdparty-ablation   <- MiniMax-M3, MiniMax-M2.7-highspeed

Two aggregation lessons are baked in, because both cost a wrong answer first:

1. **Mean of per-seed differences, not difference of means.** The reported figure is
   mean_i(V_strong,i - V_hold,i). Differencing the two arm means gives a different number
   when the seed sets are not identical, and a naive pooled mean over records is different
   again -- it produced +0.531 for Qwen3.8-27B against a published +0.431.
2. **The two batches must never be pooled.** They differ in output cap (1024 vs 8192),
   serving (local vLLM vs third-party API) and thinking policy. The overview states this;
   the appendix says the same.
"""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "e6-sources"

# appendix tab:modelinvariance, verbatim: (label, strong-hold, vs pure RL, n seeds)
PAPER = [
    ("27b", "Qwen3.8-27B", 0.431, -0.433, 13, "paper-E6-model-invariance"),
    ("8b", "Qwen3-8B", 0.464, -0.200, 13, "paper-E6-model-invariance"),
    ("m3", "MM-M3", 0.313, -0.422, 10, "paper-E6b-thirdparty-ablation"),
    ("m27h", "MM-M2.7-hs", 0.450, 0.022, 10, "paper-E6b-thirdparty-ablation"),
]


def load(batch: str) -> dict:
    p = SRC / batch / "analysis" / "e6_analysis.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    print("=" * 96)
    print("E6 four-model scan  vs  appendix tab:modelinvariance")
    print("=" * 96)

    caches: dict[str, dict] = {}
    ok = bad = 0
    print(f"\n  {'model':<16}{'n':>4}{'strong-hold':>13}{'paper':>9}{'diff':>9}  source")
    for key, label, sh_paper, _dep, n_paper, batch in PAPER:
        d = caches.setdefault(batch, load(batch))
        by: dict[tuple[str, str], dict] = {}
        for r in d.get("records", []):
            # The batch carries TWO arms: `llm-rl` (the layering condition, 13 or 10
            # seeds) and `rl` (the pure-RL reference, 3 seeds, strong only). Filtering on
            # (model, condition) alone lets the 3 `rl` records overwrite the `llm-rl`
            # values at those seeds and inflates every strong-arm mean.
            if r.get("arm") != "llm-rl":
                continue
            if isinstance(r.get("V"), (int, float)):
                by.setdefault((r["model"], r["condition"]), {})[r["seed"]] = float(r["V"])
        s = by.get((key, "strong"), {})
        h = by.get((key, "hold"), {})
        seeds = sorted(set(s) & set(h))
        if not seeds:
            print(f"  {label:<16}{'-':>4}{'not found':>13}{sh_paper:>9.3f}  {batch}")
            bad += 1
            continue
        # mean of per-seed differences
        m = st.mean(s[k] - h[k] for k in seeds)
        good = abs(m - sh_paper) <= 0.0015 and len(seeds) == n_paper
        ok += good
        bad += not good
        print(f"  {label:<16}{len(seeds):>4}{m:>13.3f}{sh_paper:>9.3f}{m - sh_paper:>+9.3f}"
              f"  {'' if good else '<-- CHECK '}{batch}")

    print(f"\n  models matching the paper exactly: {ok}/{len(PAPER)}")

    print("\n  --- the boundary finding the appendix highlights ---")
    d = caches.setdefault("paper-E6b-thirdparty-ablation",
                          load("paper-E6b-thirdparty-ablation"))
    print("     MM-M2.7-highspeed reaches parity with pure RL (+0.022, CI [0.000, 0.067]),")
    print("     i.e. the headroom premise vanishes on that model.")
    ov = SRC / "E6_family_overview.md"
    if ov.is_file():
        txt = ov.read_text(encoding="utf-8", errors="replace")
        if "184" in txt:
            print("     NOTE the overview also records this model emitted 184 thinking blocks")
            print("     across 20 cases (it was NOT asked to disable thinking) -- a confound")
            print("     the appendix does not mention.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

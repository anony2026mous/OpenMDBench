"""Seed-level audit of the legacy grid KSG coupling traces.

Recomputes the paper-aligned legacy C_info/residual-MI quantity by seed so
between-seed uncertainty is visible. The historical implementation clips
negative C_info - residual estimates to zero; this audit preserves the raw
difference and labels all outputs exploratory (not formal D3 validation).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                row = json.loads(line)
                if row.get("variant") == "layered":
                    rows.append(row)
    return rows


def seed_stats(values: dict[int, float], *, bootstraps: int, rng: np.random.Generator):
    seeds = sorted(values)
    if not seeds:
        return {"n_seeds": 0, "seeds": [], "mean": None, "sample_sd": None,
                "median": None, "bootstrap_mean_ci95": None,
                "resampling_unit": "seed_level_estimate", "bootstrap_replicates": 0}
    data = np.asarray([values[seed] for seed in seeds], dtype=float)
    sampled = rng.choice(data, size=(bootstraps, len(data)), replace=True).mean(axis=1)
    return {"n_seeds": len(seeds), "seeds": seeds, "mean": float(data.mean()),
            "sample_sd": float(data.std(ddof=1)) if len(data) > 1 else None,
            "median": float(np.median(data)),
            "bootstrap_mean_ci95": [float(x) for x in np.quantile(sampled, [0.025, 0.975])],
            "resampling_unit": "seed_level_estimate", "bootstrap_replicates": bootstraps}


def finite(value):
    return float(value) if np.isfinite(value) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--traces", nargs="+", required=True, type=Path)
    parser.add_argument("--legacy-summary", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bootstraps", type=int, default=5000)
    parser.add_argument("--rng-seed", type=int, default=20260925)
    args = parser.parse_args()
    output = args.output.resolve()
    inputs = [p.resolve() for p in args.traces]
    summaries = [p.resolve() for p in (args.legacy_summary or [])]
    if output.exists() or any(output == p or output.is_relative_to(p.parent) or p.parent.is_relative_to(output)
                              for p in inputs + summaries):
        raise ValueError("Choose a new output directory separate from immutable inputs")
    if args.bootstraps < 100:
        raise ValueError("At least 100 bootstrap replicates required")

    code_dir = Path(__file__).resolve().parents[1] / "source-code" / "openmd" / "code"
    sys.path.insert(0, str(code_dir))
    from coupling_mi import estimate_couplings

    groups = defaultdict(dict)
    files = {}
    for trace_path in inputs:
        architecture = "llm" if "_rule" not in trace_path.stem else "rule"
        files[architecture] = {"path": str(trace_path), "sha256": sha(trace_path)}
        for row in read_jsonl(trace_path):
            key = (architecture, row["task_mode"], row["granularity"])
            seed = int(row["seed"])
            if seed in groups[key]:
                raise ValueError(f"Duplicate layered seed: {key}, {seed}")
            trace = row.get("trace")
            if not isinstance(trace, list) or len(trace) == 0:
                raise ValueError(f"Invalid empty trace: {key}, seed {seed}")
            groups[key][seed] = trace

    rng = np.random.default_rng(args.rng_seed)
    rows = []
    by_cell = {}
    for key in sorted(groups):
        architecture, mode, granularity = key
        episodes = groups[key]
        if len(episodes) < 2:
            raise ValueError(f"Need at least two seeds in {key}")
        per_seed = {}
        for seed, steps in sorted(episodes.items()):
            fit = estimate_couplings([{"steps": steps}], granularity=granularity)
            c_info, residual, clipped = (finite(fit["c_info"]), finite(fit["residual_mi"]),
                                         finite(fit["b_if"]))
            raw = c_info - residual if c_info is not None and residual is not None else None
            per_seed[seed] = {"c_info": c_info, "residual_mi": residual,
                              "raw_b_if": raw,
                              "legacy_clipped_b_if": clipped, "n_windows": fit["n_windows"],
                              "trace_steps": len(steps)}
        # Preserve a separate pooled estimate for exact comparison with the
        # historical output; uncertainty is computed from independent seeds.
        pooled = estimate_couplings([{"steps": steps} for steps in episodes.values()],
                                    granularity=granularity)
        pooled_c, pooled_r, pooled_b = (finite(pooled["c_info"]), finite(pooled["residual_mi"]),
                                        finite(pooled["b_if"]))
        fields = {}
        for measure in ("c_info", "residual_mi", "raw_b_if", "legacy_clipped_b_if"):
            available = {s: v[measure] for s, v in per_seed.items() if v[measure] is not None}
            fields[measure] = seed_stats(available, bootstraps=args.bootstraps, rng=rng)
            fields[measure]["unavailable_seeds"] = sorted(set(per_seed) - set(available))
        cell = {"architecture": architecture, "task_mode": mode, "granularity": granularity,
                "per_seed": per_seed, "seed_level_summaries": fields,
                "pooled_reproduction": {"c_info": pooled_c,
                                        "residual_mi": pooled_r,
                                        "raw_b_if": pooled_c - pooled_r if pooled_c is not None and pooled_r is not None else None,
                                        "legacy_clipped_b_if": pooled_b,
                                        "n_windows": pooled["n_windows"]},
                "legacy_clipped_seed_count": sum(v["raw_b_if"] is not None and v["raw_b_if"] < 0 for v in per_seed.values()),
                "estimand_note": "KSG cross-domain coupling reduction over 3-step windows; not direct I(G;S)"}
        rows.append(cell)
        by_cell[key] = per_seed

    paired = []
    for architecture in sorted({key[0] for key in by_cell}):
        for mode in sorted({key[1] for key in by_cell if key[0] == architecture}):
            weak = by_cell[(architecture, mode, "weak")]
            strong = by_cell[(architecture, mode, "strong")]
            common = sorted(seed for seed in set(weak) & set(strong)
                            if weak[seed]["raw_b_if"] is not None and strong[seed]["raw_b_if"] is not None)
            delta = {seed: strong[seed]["raw_b_if"] - weak[seed]["raw_b_if"] for seed in common}
            paired.append({"architecture": architecture, "task_mode": mode,
                           "contrast": "strong_minus_weak_raw_b_if", "paired_seed_delta": delta,
                           "summary": seed_stats(delta, bootstraps=args.bootstraps, rng=rng),
                           "d3_direction_passed": False})

    legacy_comparisons = []
    for summary_path in summaries:
        doc = json.loads(summary_path.read_text(encoding="utf-8"))
        for old in doc.get("cells", []):
            architecture = "llm" if doc.get("config", {}).get("llm") else "rule"
            key = (architecture, old["task_mode"], old["granularity"])
            match = next((row for row in rows if (row["architecture"], row["task_mode"], row["granularity"]) == key), None)
            if match:
                old_b = old["b_if"]
                new_b = match["pooled_reproduction"]["legacy_clipped_b_if"]
                legacy_comparisons.append({"summary_file": str(summary_path),
                                           "architecture": architecture,
                                           "task_mode": old["task_mode"],
                                           "granularity": old["granularity"],
                                           "legacy_json_b_if": old_b,
                                           "trace_recomputed_pooled_clipped_b_if": new_b,
                                           "absolute_difference": abs(old_b - new_b) if new_b is not None else None})

    result = {"schema": "role-c-legacy-grid-ksg-seed-audit@1",
              "input_trace_manifests": files,
              "legacy_summaries": [{"path": str(p), "sha256": sha(p)} for p in summaries],
              "implementation": str(Path(__file__).resolve()), "implementation_sha256": sha(Path(__file__)),
              "estimator_source": str((code_dir / "coupling_mi.py").resolve()),
              "estimator_sha256": sha(code_dir / "coupling_mi.py"),
              "groups": rows, "paired_tier_contrasts": paired,
              "legacy_reproduction_checks": legacy_comparisons,
              "legacy_reproduction_max_abs_error": max((r["absolute_difference"] for r in legacy_comparisons
                                                         if r["absolute_difference"] is not None), default=None),
              "formal_B_if_validated": False, "formal_D3_passed": False,
              "limitations": ["B_if is the historical C_info - residual-MI proxy, not direct goal-state MI.",
                              "Historical B_if clips negative noisy differences to zero; raw differences are retained here.",
                              "Three-step temporal windows remain dependent; seed bootstrap captures between-seed, not within-trace estimator uncertainty.",
                              "Legacy traces and this recomputation do not satisfy the high-fidelity IE-01..08 hybrid requirement.",
                              "No post hoc gradient claim is made; D3 remains not validated."]}
    output.mkdir(parents=True)
    (output / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                                            encoding="utf-8")
    print(json.dumps({"groups": len(rows), "paired_contrasts": len(paired),
                      "legacy_comparison_rows": len(legacy_comparisons),
                      "legacy_reproduction_max_abs_error": result["legacy_reproduction_max_abs_error"],
                      "formal_B_if_validated": False, "formal_D3_passed": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

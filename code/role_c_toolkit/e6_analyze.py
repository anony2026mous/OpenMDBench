"""Read-only E6 analysis: paired seed comparison of two models on one frozen pipeline.

No file inside a run directory is modified; the only writes are ``analysis/*.json``,
``analysis/per_case.csv`` and the optional Markdown summary.  Every verdict is
computed from the preregistered plan, and a criterion that cannot be evaluated is
reported as such instead of being silently passed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

BOOTSTRAP_SEED = 20261003
BOOTSTRAP_DRAWS = 10000
CONDITIONS = ("strong", "hold")


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def percentile(values, q):
    ordered = sorted(values)
    if not ordered:
        return None
    x = (len(ordered) - 1) * q
    left, right = math.floor(x), math.ceil(x)
    return ordered[left] + (ordered[right] - ordered[left]) * (x - left)


def bootstrap(values, draws=BOOTSTRAP_DRAWS):
    values = list(values)
    if len(values) < 3:
        return {"mean": statistics.fmean(values) if values else None, "ci95": None,
                "unit": "seed", "n": len(values), "draws": 0,
                "interpretation": "too few seeds for a bootstrap interval"}
    rng = random.Random(BOOTSTRAP_SEED)
    means = []
    for _ in range(draws):
        sample = [values[rng.randrange(len(values))] for _ in values]
        means.append(statistics.fmean(sample))
    return {"mean": statistics.fmean(values), "ci95": [percentile(means, .025), percentile(means, .975)],
            "unit": "seed", "n": len(values), "draws": draws,
            "rng": "MersenneTwister", "seed": BOOTSTRAP_SEED,
            "interpretation": "seed-resampled interval over the preregistered seed set"}


def relocate(path: Path, run_dir: Path) -> Path:
    """Resolve a result path that was recorded on another machine.

    A run directory copied back from the server keeps absolute server paths in
    ``status.json``.  Only the ``episodes/<case>/<file>`` tail is meaningful, so fall
    back to the local copy when the recorded absolute path is absent.
    """
    if path.exists():
        return path
    parts = path.parts
    for anchor in ('episodes',):
        if anchor in parts:
            index = parts.index(anchor)
            candidate = Path(run_dir).joinpath(*parts[index:])
            if candidate.exists():
                return candidate
    return path


def load_records(run_dirs, plan_path: Path):
    """Merge one or more per-model run directories that share a frozen plan."""
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    records, problems, states, seen = [], [], {}, set()
    for run_dir in run_dirs:
        run_dir = Path(run_dir)
        state = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        states[str(run_dir)] = {"status": state["status"],
                                "failures": [row["case_id"] for row in state.get("failures") or []],
                                "completed": len(state["completed"])}
        for entry in state["completed"]:
            path = relocate(Path(entry["result"]), run_dir)
            if not path.exists():
                problems.append({"case_id": entry["case_id"], "problem": "missing_result"})
                continue
            if entry.get("sha256") and sha(path) != entry["sha256"]:
                raise ValueError("Case result changed after the run: " + str(path))
            result = json.loads(path.read_text(encoding="utf-8"))
            if result["model"] not in plan["models"]:
                problems.append({"case_id": entry["case_id"], "problem": "unknown_model"})
                continue
            key = (result["model"], result["condition"], result["seed"], result["arm"])
            if key in seen:
                problems.append({"case_id": entry["case_id"], "problem": "duplicate_case"})
                continue
            seen.add(key)
            expected_name = plan["models"][result["model"]]["served_name"]
            native = relocate(Path(result.get("native_report") or ""), run_dir)
            if result["arm"] == "llm-rl":
                if result.get("served_name") != expected_name:
                    problems.append({"case_id": entry["case_id"], "problem": "served_name_mismatch"})
                if not native.is_file():
                    problems.append({"case_id": entry["case_id"], "problem": "native_report_missing"})
                elif entry["case_id"] not in native.parts:
                    problems.append({"case_id": entry["case_id"],
                                     "problem": "native_report_path_mismatch"})
            costs = result.get("costs") or {}
            records.append({
                "case_id": entry["case_id"], "model": result["model"],
                "condition": result["condition"], "seed": result["seed"], "arm": result["arm"],
                "V": result["V"], "analysis_valid": result["analysis_valid"],
                "invalid_reasons": result.get("invalid_reasons") or [],
                "steps": result.get("steps"), "llm_calls": costs.get("llm_calls"),
                "API_total_tokens": costs.get("actual_API_total_tokens"),
                "llm_seconds": costs.get("request_seconds"),
                "wall_seconds": costs.get("episode_wall_seconds"),
                "served_name": result.get("served_name"), "endpoint": result.get("endpoint"),
                "planner_fallback_count": (result.get("agent_stats") or {}).get("fallback_count"),
                "goai_rejected": (result.get("agent_stats") or {}).get("goai_rejected"),
                "thinking_blocks": result.get("thinking_blocks"),
                "expect_no_thinking": result.get("expect_no_thinking"),
                "stop_reasons": result.get("stop_reasons"),
                "provider": result.get("provider"),
                "run_dir": str(run_dir),
                "result_path": str(path), "result_sha256": sha(path),
            })
    return plan, records, problems, states


def analyze(run_dirs, plan_path: Path, analysis_dir: Path | None = None) -> dict:
    plan, records, problems, states = load_records(run_dirs, plan_path)
    seeds = list(plan["seeds"])
    reference_seeds = list(plan["reference_seeds"])
    # Two different key spaces: analysed cases use (model, condition, seed) and the
    # pure-RL reference uses (model, seed) under condition "strong".  Keeping them apart
    # is what makes the completeness check meaningful.
    expected = {(model, condition, seed) for model in plan["models"] for condition in CONDITIONS
                for seed in seeds}
    expected_reference = {(model, seed) for model in plan["models"] for seed in reference_seeds}
    by_key = {(row["model"], row["condition"], row["seed"]): row for row in records
              if row["arm"] == "llm-rl"}
    lookup = set(by_key)
    # The pure-RL reference shares the (model, seed) key space with the strong arm, so
    # keep it in its own table before any verdict reads it.
    reference_rows = {(row["model"], row["seed"]): row for row in records if row["arm"] == "rl"}

    # Endpoint continuity: the same service processes must still be the ones probed,
    # otherwise the batches were not served by the frozen set.
    probe_path = Path(plan_path).parent / "endpoints.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.exists() else None
    continuity = []
    proc_available = Path("/proc").is_dir()
    continuity_note = ("checked against /proc" if proc_available else
                       "not checkable on this platform (no /proc); re-run the analyzer on the "
                       "machine that served the batches to verify process continuity")
    if probe and proc_available:
        for row in probe["records"]:
            for metric in row.get("metrics_pids") or []:
                try:
                    text = Path("/proc", str(metric["pid"]), "stat").read_text()
                    now = text[text.rfind(")") + 2:].split()[19]
                except (FileNotFoundError, ProcessLookupError):
                    now = None
                continuity.append({"model": row["model"], "replica": row["replica"],
                                   "pid": metric["pid"],
                                   "same_process_start": now == metric["start_ticks"]})
    provider_identity = [
        {"model": row.get("model"), "served_name": row.get("served_name"),
         "base_url": row.get("base_url"), "available_models": row.get("available_models"),
         "thinking_blocks_at_probe": row.get("thinking_blocks"),
         "expect_no_thinking": row.get("expect_no_thinking")}
        for row in (probe["records"] if probe else []) if row.get("kind") == "remote-provider"]

    summary = {
        "schema": "E6-model-invariance-analysis@1",
        "run_status": {Path(path).name: row["status"] for path, row in states.items()},
        "run_directories": states,
        "plan_sha256": sha(plan_path),
        "analyzer_sha256": sha(Path(__file__)),
        "models": {name: {key: entry.get(key) for key in
                          ("served_name", "kind", "provider", "base_url", "directory",
                           "manifest_sha256", "max_model_len", "thinking_policy",
                           "expect_no_thinking") if key in entry}
                   for name, entry in plan["models"].items()},
        "conditions": list(CONDITIONS),
        "seeds": seeds, "reference_seeds": reference_seeds,
        "records": records, "data_problems": problems,
        "endpoint_continuity": continuity,
        "endpoint_continuity_note": continuity_note,
        "provider_identity": provider_identity,
        "all_preregistered_cases_present": bool(
            lookup == expected and set(reference_rows) == expected_reference),
        "all_preregistered_cases_valid": bool(
            lookup == expected and set(reference_rows) == expected_reference and
            all(row["analysis_valid"] for row in records) and not problems),
        "no_cross_batch_data_merged": True,
        "utility_definition": ("Frozen grid blue_score = 0.6*mission_success + "
                               "0.2*red_combatant_elimination_fraction + 0.2*blue_survival_fraction"),
        "group_summary": {}, "verdicts": {},
        "masked_condition_available": False,
        "condition_note": ("The pipeline exposes only strong/hold goal modes; the masked dose "
                           "point from the older checklist does not exist in this code"),
        "thinking_summary": {
            model: {"thinking_blocks": sum(int(row.get("thinking_blocks") or 0)
                                           for row in records if row["model"] == model),
                    "cases_with_thinking": sum(1 for row in records if row["model"] == model
                                               and (row.get("thinking_blocks") or 0) > 0),
                    "expect_no_thinking": next((row.get("expect_no_thinking") for row in records
                                                if row["model"] == model), None)}
            for model in plan["models"]},
    }

    groups = {}
    for model in plan["models"]:
        groups[model] = {}
        for condition in CONDITIONS:
            rows = [by_key[(model, condition, seed)] for seed in seeds
                    if (model, condition, seed) in by_key
                    and by_key[(model, condition, seed)]["analysis_valid"]]
            groups[model][condition] = bootstrap([row["V"] for row in rows])
            groups[model][condition]["seeds_used"] = [row["seed"] for row in rows]
            groups[model][condition]["invalid_or_missing"] = \
                [seed for seed in seeds if (model, condition, seed) not in by_key
                 or not by_key[(model, condition, seed)]["analysis_valid"]]
        pairs = [by_key[(model, "strong", seed)]["V"] - by_key[(model, "hold", seed)]["V"]
                 for seed in seeds
                 if (model, "strong", seed) in by_key and (model, "hold", seed) in by_key
                 and by_key[(model, "strong", seed)]["analysis_valid"]
                 and by_key[(model, "hold", seed)]["analysis_valid"]]
        groups[model]["strong_minus_hold"] = bootstrap(pairs)
        groups[model]["strong_minus_hold"]["per_seed"] = {
            str(seed): (by_key[(model, "strong", seed)]["V"] - by_key[(model, "hold", seed)]["V"])
            for seed in seeds if (model, "strong", seed) in by_key and (model, "hold", seed) in by_key}
    summary["group_summary"] = groups

    for model in plan["models"]:
        values = []
        for seed in reference_seeds:
            strong = by_key.get((model, "strong", seed))
            reference = reference_rows.get((model, seed))
            if strong and reference and strong["analysis_valid"] and reference["analysis_valid"]:
                values.append(strong["V"] - reference["V"])
        groups[model]["strong_minus_pure_rl"] = bootstrap(values)
        groups[model]["strong_minus_pure_rl"]["seeds_used"] = [
            seed for seed in reference_seeds
            if (model, "strong", seed) in lookup and (model, seed) in reference_rows]

    for model in plan["models"]:
        interface = groups[model]["strong_minus_hold"]
        behind = groups[model]["strong_minus_pure_rl"]
        if interface["ci95"] is None:
            interface_verdict = "not_evaluable_insufficient_valid_seeds"
        elif interface["ci95"][0] > 0:
            interface_verdict = "passed"
        elif interface["mean"] > 0:
            interface_verdict = "not_significant_ci_includes_zero"
        else:
            interface_verdict = "failed"
        if not behind["seeds_used"]:
            behind_verdict = "not_evaluable_no_reference"
        elif behind["mean"] < 0:
            behind_verdict = "passed"
        else:
            behind_verdict = "failed"
        summary["verdicts"][model] = {
            "interface_causal_necessity": interface_verdict,
            "deployment_behind_baseline": behind_verdict,
            "overall": ("reproduced" if interface_verdict == "passed" and behind_verdict == "passed"
                        else "not_reproduced"),
        }
    if not summary["all_preregistered_cases_present"]:
        summary["verdicts"]["_run"] = "incomplete_preregistered_case_set"
    if continuity and not all(row["same_process_start"] for row in continuity):
        summary["verdicts"]["_services"] = "serving_process_changed_during_the_batches"

    analysis_dir = Path(analysis_dir) if analysis_dir else Path(list(states)[0]) / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "e6_analysis.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + chr(10), encoding="utf-8")
    fields = ["case_id", "model", "condition", "arm", "seed", "V", "analysis_valid",
              "invalid_reasons", "steps", "llm_calls", "API_total_tokens", "llm_seconds",
              "wall_seconds", "served_name", "endpoint", "planner_fallback_count",
              "thinking_blocks", "expect_no_thinking", "provider", "run_dir"]
    with (analysis_dir / "per_case.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True, help="the frozen plan.json")
    parser.add_argument("--run-dir", type=Path, action="append", required=True,
                        help="per-model run directory; repeat for each model")
    parser.add_argument("--analysis-dir", type=Path,
                        help="where to write e6_analysis.json and per_case.csv")
    parser.add_argument("--summary-md", type=Path)
    args = parser.parse_args()
    summary = analyze(args.run_dir, args.plan, args.analysis_dir)
    if args.summary_md:
        plan = json.loads(Path(args.plan).read_text(encoding='utf-8'))
        from e6_summary import render
        args.summary_md.write_text(render(summary, plan), encoding='utf-8')
        print("wrote", args.summary_md, flush=True)
    print(json.dumps({"verdicts": summary["verdicts"],
                      "all_valid": summary["all_preregistered_cases_valid"],
                      "analysis": str(args.analysis_dir or args.run_dir[0])},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

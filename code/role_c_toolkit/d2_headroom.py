"""D2 headroom analysis for the E4 scenario families (read-only).

Reads a calibration plan plus its recorded state, computes the per-scenario, per-policy
success rate over seeds, and derives the D2 gate value: the *best pure baseline*
success rate must land inside [40%, 85%].

Success is the native terminal outcome ``objective_complete``; a case whose episode never
reached a terminal is reported as unusable rather than counted as a failure.  Seeds are
the sampling unit, so the interval is a seed bootstrap.

Usage:
    python d2_headroom.py --plan <plan.json> --state <plan.state.json> \
                          --output <d2_headroom.json> [--csv <per_case.csv>]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

SUCCESS_OUTCOME = "objective_complete"
# The two policies in each case pair are a floor/control and a task-relevant baseline.
FLOOR_POLICIES = {"idle", "indiscriminate", "naive"}
D2_LOW, D2_HIGH = 0.40, 0.85


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def merge_plans(plan_paths: list[Path], state_paths: list[Path]) -> tuple[dict, dict, dict]:
    """Merge several single-seed plans (and their states) into one seed-major view.

    The calibration tool keeps one plan per seed so seeds can run in parallel; analysis still
    needs them together.  A case id that appears in more than one input is kept once and the
    duplicate is reported, never silently averaged.
    """
    cases, case_states, duplicates = [], {}, []
    for plan_path, state_path in zip(plan_paths, state_paths):
        plan = load(plan_path)
        state = load(state_path)
        for case in plan["cases"]:
            if case["case_id"] in case_states:
                duplicates.append(case["case_id"])
                continue
            cases.append(case)
        for case_id, entry in state["cases"].items():
            if case_id in case_states:
                continue
            case_states[case_id] = entry
    return ({"cases": cases}, {"cases": case_states},
            {"plans": [str(path) for path in plan_paths],
             "states": [str(path) for path in state_paths],
             "cases": len(cases), "duplicate_case_ids": duplicates})


def plan_lookup(plan: dict) -> dict:
    """Case metadata (seed, scenario, difficulty, policy) lives in the plan, not the state."""
    return {case["case_id"]: case for case in plan["cases"]}


def cases_from_state(state: dict, plan: dict | None = None) -> list[dict]:
    lookup = plan_lookup(plan) if plan else {}
    rows = []
    for case_id, entry in state["cases"].items():
        if entry.get("status") != "recorded":
            continue
        declared = lookup.get(case_id, {})
        terminal = entry.get("terminal") or {}
        rows.append({
            "case_id": case_id,
            "scenario_id": declared.get("scenario_id"),
            "policy": declared.get("expected_policy"),
            "seed": declared.get("seed"),
            "difficulty": declared.get("difficulty"),
            "side": declared.get("side"),
            "final_tick": entry.get("final_tick"),
            "outcome": terminal.get("outcome") if isinstance(terminal, dict) else None,
            "rule_id": terminal.get("rule_id") if isinstance(terminal, dict) else None,
            "success": (terminal.get("outcome") == SUCCESS_OUTCOME)
            if isinstance(terminal, dict) else None,
            "full_episode_completed": bool(entry.get("full_episode_completed")),
            "native_status": entry.get("native_status"),
            "native_failure": entry.get("native_failure"),
            "evidence": entry.get("evidence"),
        })
    return rows


def bootstrap_ci(values: list[float], draws: int = 10000, rng_seed: int = 20261003) -> list[float]:
    if not values:
        return [None, None]
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(rng_seed)
    means = []
    n = len(values)
    for _ in range(draws):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return [means[int(0.025 * draws)], means[int(0.975 * draws)]]


def analyse(rows: list[dict]) -> dict:
    by_scenario_policy: dict[tuple[str, str], dict[int, bool]] = defaultdict(dict)
    unusable = []
    for row in rows:
        if row["seed"] is None or row["policy"] is None or row["scenario_id"] is None:
            unusable.append(row)
            continue
        if not row["full_episode_completed"] or row["success"] is None:
            unusable.append(row)
            continue
        by_scenario_policy[(row["scenario_id"], row["policy"])][row["seed"]] = row["success"]

    scenarios: dict[str, dict] = {}
    for (scenario, policy), per_seed in sorted(by_scenario_policy.items()):
        flags = [1.0 if flag else 0.0 for _seed, flag in sorted(per_seed.items())]
        entry = scenarios.setdefault(scenario, {"policies": {}})
        entry["policies"][policy] = {
            "seeds": len(flags), "successes": int(sum(flags)),
            "success_rate": (sum(flags) / len(flags)) if flags else None,
            "ci95": bootstrap_ci(flags),
            "is_floor_control": policy in FLOOR_POLICIES,
        }
    for scenario, entry in scenarios.items():
        usable = {name: value for name, value in entry["policies"].items()
                  if value["success_rate"] is not None}
        if usable:
            best = max(usable.items(), key=lambda item: (item[1]["success_rate"], item[0]))
            entry["best_baseline_policy"] = best[0]
            entry["best_baseline_success_rate"] = best[1]["success_rate"]
            entry["best_baseline_ci95"] = best[1]["ci95"]
            entry["best_baseline_note"] = (
                "floor control only (no task-relevant baseline recorded)"
                if all(value["is_floor_control"] for value in usable.values()) else None)
            entry["d2_headroom_verdict"] = (
                "pass" if D2_LOW <= best[1]["success_rate"] <= D2_HIGH else "fail")
        else:
            entry["best_baseline_policy"] = None
            entry["best_baseline_success_rate"] = None
            entry["d2_headroom_verdict"] = "not_evaluable"
    return {
        "schema": "e4-d2-headroom@1",
        "success_criterion": {"outcome": SUCCESS_OUTCOME, "source": "native terminal"},
        "gate": {"low": D2_LOW, "high": D2_HIGH,
                 "operationalisation": "best pure baseline SR within [0.40, 0.85]",
                 "note": ("success rate is a fraction of seeds, so with 5 seeds only "
                          "0.4 / 0.6 / 0.8 can pass; report the rate and the CI, never "
                          "the verdict alone")},
        "n_cases": len(rows),
        "n_unusable": len(unusable),
        "unusable_cases": [row["case_id"] for row in unusable],
        "scenarios": scenarios,
        "counts": {
            "scenarios": len(scenarios),
            "pass": sum(1 for entry in scenarios.values()
                        if entry["d2_headroom_verdict"] == "pass"),
            "fail": sum(1 for entry in scenarios.values()
                        if entry["d2_headroom_verdict"] == "fail"),
            "not_evaluable": sum(1 for entry in scenarios.values()
                                 if entry["d2_headroom_verdict"] == "not_evaluable"),
        },
    }


def per_case_csv(rows: list[dict]) -> str:
    lines = ["case_id,scenario_id,policy,seed,outcome,rule_id,success,final_tick,evidence"]
    for row in sorted(rows, key=lambda item: item["case_id"]):
        lines.append(",".join(str(row[key]) for key in
                              ("case_id", "scenario_id", "policy", "seed", "outcome", "rule_id",
                               "success", "final_tick", "evidence")))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, action="append", required=True,
                        help="repeat once per seed plan; several plans are merged seed-major")
    parser.add_argument("--state", type=Path, action="append", required=True,
                        help="state file for each plan, in the same order")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if len(args.plan) != len(args.state):
        raise SystemExit("provide one --state per --plan")
    plan, state, merge = merge_plans(args.plan, args.state)
    rows = cases_from_state(state, plan)
    summary = analyse(rows)
    summary["plan"] = merge["plans"] if len(merge["plans"]) > 1 else merge["plans"][0]
    summary["state"] = merge["states"] if len(merge["states"]) > 1 else merge["states"][0]
    summary["merged_inputs"] = merge
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    if args.csv:
        args.csv.write_text(per_case_csv(rows), encoding="utf-8")
    print(json.dumps({"cases": summary["n_cases"], "unusable": summary["n_unusable"],
                      "counts": summary["counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

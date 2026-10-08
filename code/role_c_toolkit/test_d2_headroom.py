"""Offline tests for the D2 headroom analyzer.

The D2 verdict is a gate value that goes into appendix A, so the tests pin the two
things that could silently corrupt it: counting a non-terminal episode as a failure, and
picking a floor control as "the best pure baseline".
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location('d2_headroom_under_test',
                                              ROOT / 'd2_headroom.py')
d2 = importlib.util.module_from_spec(spec)
sys.modules['d2_headroom_under_test'] = d2
spec.loader.exec_module(d2)


def make_plan(scenario_policy_seeds):
    """case_id mirrors the runner's ``<seed>-<scenario>-<difficulty>-<side>``; each policy
    gets its own side so the two cases of one scenario never share an id."""
    cases = []
    sides = ("A", "B")
    for index, ((scenario, policy), seeds) in enumerate(scenario_policy_seeds.items()):
        side = sides[index % len(sides)]
        for seed in seeds:
            cases.append({"case_id": f"{seed}-{scenario}-standard-{side}", "seed": seed,
                          "scenario_id": scenario, "difficulty": "standard", "side": side,
                          "expected_policy": policy})
    return {"cases": cases}


def make_state(outcomes):
    """outcomes: case_id -> 'objective_complete' | 'objective_incomplete' | None (no terminal)"""
    state = {"cases": {}}
    for case_id, outcome in outcomes.items():
        complete = outcome is not None
        state["cases"][case_id] = {
            "status": "recorded", "full_episode_completed": complete,
            "native_status": "ok", "native_failure": None, "final_tick": 100,
            "evidence": f"evidence/{case_id}.json",
            "terminal": {"outcome": outcome, "rule_id": "rule.success"} if complete else None,
        }
    return state


def build(scenario_policy_seeds, outcomes):
    plan = make_plan(scenario_policy_seeds)
    state = make_state(outcomes)
    return d2.analyse(d2.cases_from_state(state, plan))


class HeadroomTests(unittest.TestCase):
    def test_success_rate_and_best_policy_pick(self):
        seeds = [2001, 2002, 2003, 2004, 2005]
        plan_spec = {("MD-REC-002", "sweep"): seeds, ("MD-REC-002", "idle"): seeds}
        outcomes = {}
        # sweep: 3 of 5 complete -> 0.6 (pass); idle: 0 of 5 -> floored control
        for index, seed in enumerate(seeds):
            outcomes[f"{seed}-MD-REC-002-standard-A"] = (
                "objective_complete" if index < 3 else "objective_incomplete")
            outcomes[f"{seed}-MD-REC-002-standard-B"] = "objective_incomplete"
        summary = build(plan_spec, outcomes)
        entry = summary["scenarios"]["MD-REC-002"]
        self.assertEqual(entry["best_baseline_policy"], "sweep")
        self.assertAlmostEqual(entry["best_baseline_success_rate"], 0.6)
        self.assertEqual(entry["d2_headroom_verdict"], "pass")
        self.assertEqual(summary["counts"], {"scenarios": 1, "pass": 1, "fail": 0,
                                             "not_evaluable": 0})

    def test_saturated_baseline_fails_the_gate(self):
        seeds = [2001, 2002, 2003, 2004, 2005]
        plan_spec = {("MD-TRK-001", "follow"): seeds}
        outcomes = {f"{seed}-MD-TRK-001-standard-A": "objective_complete" for seed in seeds}
        summary = build(plan_spec, outcomes)
        entry = summary["scenarios"]["MD-TRK-001"]
        self.assertEqual(entry["best_baseline_success_rate"], 1.0)
        self.assertEqual(entry["d2_headroom_verdict"], "fail")  # no headroom left

    def test_floor_baseline_fails_the_gate(self):
        seeds = [2001, 2002, 2003, 2004, 2005]
        plan_spec = {("MD-AD-001", "indiscriminate"): seeds}
        outcomes = {f"{seed}-MD-AD-001-standard-A": "objective_incomplete" for seed in seeds}
        summary = build(plan_spec, outcomes)
        entry = summary["scenarios"]["MD-AD-001"]
        self.assertEqual(entry["d2_headroom_verdict"], "fail")  # floored, no contrast
        self.assertTrue(entry["policies"]["indiscriminate"]["is_floor_control"])

    def test_episode_without_terminal_is_unusable_not_a_failure(self):
        seeds = [2001, 2002]
        plan_spec = {("MD-ER-001", "safe"): seeds}
        outcomes = {"2001-MD-ER-001-standard-A": "objective_complete",
                    "2002-MD-ER-001-standard-A": None}  # never terminated
        summary = build(plan_spec, outcomes)
        self.assertEqual(summary["n_unusable"], 1)
        self.assertEqual(summary["unusable_cases"], ["2002-MD-ER-001-standard-A"])
        entry = summary["scenarios"]["MD-ER-001"]
        self.assertEqual(entry["policies"]["safe"]["seeds"], 1)
        self.assertEqual(entry["best_baseline_success_rate"], 1.0)

    def test_seed_bootstrap_interval_is_reported(self):
        seeds = [2001, 2002, 2003, 2004, 2005]
        plan_spec = {("MD-REC-003", "coordinated"): seeds}
        outcomes = {}
        for index, seed in enumerate(seeds):
            outcomes[f"{seed}-MD-REC-003-standard-A"] = (
                "objective_complete" if index < 2 else "objective_incomplete")
        summary = build(plan_spec, outcomes)
        ci = summary["scenarios"]["MD-REC-003"]["best_baseline_ci95"]
        self.assertEqual(len(ci), 2)
        self.assertLessEqual(ci[0], 0.4)
        self.assertGreaterEqual(ci[1], 0.4)

    def test_merge_plans_keeps_one_copy_of_a_shared_case(self):
        """Seeds run as separate plans; merging must not double-count or drop a case."""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            plan_a = {"cases": [
                {"case_id": "2001-A-standard-A", "seed": 2001, "scenario_id": "MD-A",
                 "difficulty": "standard", "expected_policy": "sweep"},
                {"case_id": "shared-case", "seed": 2001, "scenario_id": "MD-A",
                 "difficulty": "standard", "expected_policy": "guard"}]}
            plan_b = {"cases": [
                {"case_id": "shared-case", "seed": 2002, "scenario_id": "MD-A",
                 "difficulty": "standard", "expected_policy": "guard"},
                {"case_id": "2002-A-standard-A", "seed": 2002, "scenario_id": "MD-A",
                 "difficulty": "standard", "expected_policy": "sweep"}]}
            (root / "a.json").write_text(json.dumps(plan_a), encoding="utf-8")
            (root / "b.json").write_text(json.dumps(plan_b), encoding="utf-8")
            state_a = make_state({"2001-A-standard-A": "objective_complete",
                                  "shared-case": "objective_complete"})
            state_b = make_state({"shared-case": "objective_incomplete",
                                  "2002-A-standard-A": "objective_incomplete"})
            (root / "a.state.json").write_text(json.dumps(state_a), encoding="utf-8")
            (root / "b.state.json").write_text(json.dumps(state_b), encoding="utf-8")
            plan, state, merge = d2.merge_plans([root / "a.json", root / "b.json"],
                                                [root / "a.state.json", root / "b.state.json"])
            self.assertEqual(len(plan["cases"]), 3)
            self.assertEqual(merge["duplicate_case_ids"], ["shared-case"])
            self.assertEqual(len(state["cases"]), 3)
            # the first occurrence wins, so the duplicate is reported rather than averaged
            self.assertEqual(state["cases"]["shared-case"]["terminal"]["outcome"],
                             "objective_complete")
            summary = d2.analyse(d2.cases_from_state(state, plan))
            self.assertEqual(summary["scenarios"]["MD-A"]["policies"]["sweep"]["seeds"], 2)
            self.assertEqual(summary["scenarios"]["MD-A"]["policies"]["guard"]["seeds"], 1)

    def test_cli_writes_json_and_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            seeds = [2001, 2002]
            plan = make_plan({("MD-REC-001", "sweep"): seeds})
            state = make_state({f"{seed}-MD-REC-001-standard-A": "objective_complete"
                                for seed in seeds})
            (root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
            (root / 'state.json').write_text(json.dumps(state), encoding='utf-8')
            argv = sys.argv
            sys.argv = ['d2_headroom.py', '--plan', str(root / 'plan.json'),
                        '--state', str(root / 'state.json'),
                        '--output', str(root / 'out.json'), '--csv', str(root / 'out.csv')]
            try:
                d2.main()
            finally:
                sys.argv = argv
            out = json.loads((root / 'out.json').read_text(encoding='utf-8'))
            self.assertEqual(out["counts"]["scenarios"], 1)
            self.assertIn("case_id,scenario_id,policy,seed", (root / 'out.csv').read_text(
                encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

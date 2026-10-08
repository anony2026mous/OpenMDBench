"""Offline tests for the graded (declared-composite) headroom analyzer.

The graded number goes into appendix A next to the pre-registered binary gate, so the tests
pin: the weighted-sum contract, minimised-metric signs, coverage accounting, difficulty
variant keys, and that a missing report is unusable rather than a zero.
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

for module_name in ("d2_headroom", "d2_headroom_graded"):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / f"{module_name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
graded = sys.modules["d2_headroom_graded"]

SCENARIO_YAML = """schema_version: package@2.0
scenario:
  scenario_id: md_rec_002_standard.v1
  display_name: test scenario
  scoring:
    aggregation: sum
    aggregation_version: utility-v1
    direction: maximize
    weight_policy: normalized_sum_one
    metrics:
      - id: metric.discovery
        weight: 0.5
        aggregation: mean
        direction: maximize
      - id: metric.gap
        weight: 0.5
        aggregation: mean
        direction: minimize
"""


def make_package(root: Path) -> Path:
    for name in ("md_rec_002_standard", "md_rec_001_easy", "md_rec_001_hard"):
        package = root / name
        package.mkdir(parents=True)
        text = SCENARIO_YAML if name != "md_rec_001_easy" else SCENARIO_YAML.replace(
            "md_rec_002_standard", "md_rec_001_easy")
        (package / "scenario.yaml").write_text(text, encoding="utf-8")
    return root


def row(case_id, scenario, policy, seed=2001, scores=None, success=True, complete=True):
    return {"case_id": case_id, "scenario_id": scenario, "policy": policy, "seed": seed,
            "difficulty": "standard", "final_tick": 100, "outcome": (
                "objective_complete" if success else "objective_incomplete"),
            "rule_id": "rule.success", "success": success,
            "full_episode_completed": complete, "native_status": "ok", "native_failure": None,
            "evidence": f"evidence/{case_id}.json", "scores": scores or {}}


class GradedTests(unittest.TestCase):
    def test_composite_is_the_declared_weighted_sum(self):
        policy = {"weights": {"metric.discovery": {"weight": 0.5, "direction": "maximize"},
                             "metric.gap": {"weight": 0.5, "direction": "maximize"}}}
        entry = graded.composite_of({"metric.discovery": 0.8, "metric.gap": 0.4}, policy)
        self.assertAlmostEqual(entry["composite"], 0.6)
        self.assertEqual(entry["covered_weight"], 1.0)
        self.assertEqual(entry["missing_metrics"], [])

    def test_minimised_metrics_enter_as_one_minus_value(self):
        policy = {"weights": {"metric.discovery": {"weight": 0.5, "direction": "maximize"},
                             "metric.gap": {"weight": 0.5, "direction": "minimize"}}}
        entry = graded.composite_of({"metric.discovery": 1.0, "metric.gap": 0.2}, policy)
        self.assertAlmostEqual(entry["composite"], 0.9)  # 0.5*1 + 0.5*(1-0.2)
        self.assertEqual(entry["terms"]["metric.gap"], 0.8)

    def test_missing_metric_renormalises_and_reports_coverage(self):
        policy = {"weights": {"metric.discovery": {"weight": 0.5, "direction": "maximize"},
                             "metric.gap": {"weight": 0.5, "direction": "maximize"}}}
        entry = graded.composite_of({"metric.discovery": 0.8}, policy)
        self.assertAlmostEqual(entry["composite"], 0.8)  # renormalised over covered weight
        self.assertEqual(entry["covered_weight"], 0.5)
        self.assertEqual(entry["missing_metrics"], ["metric.gap"])

    def test_no_metric_at_all_is_not_scored_as_zero(self):
        policy = {"weights": {"metric.discovery": {"weight": 0.5, "direction": "maximize"}}}
        entry = graded.composite_of({}, policy)
        self.assertIsNone(entry["composite"])
        self.assertEqual(entry["covered_weight"], 0.0)

    def test_short_metric_names_are_accepted(self):
        policy = {"weights": {"metric.discovery": {"weight": 1.0, "direction": "maximize"}}}
        self.assertAlmostEqual(graded.composite_of({"discovery": 0.3}, policy)["composite"], 0.3)

    def test_difficulty_variants_get_distinct_keys(self):
        self.assertEqual(graded.contract_key("MD-REC-001", "easy"), "MD-REC-001-EASY")
        self.assertEqual(graded.contract_key("MD-REC-001", "hard"), "MD-REC-001-HARD")
        self.assertEqual(graded.contract_key("MD-REC-002", "standard"), "MD-REC-002")

    def test_analyse_reports_bands_families_and_floor_picks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            policies = graded.scoring_policy(make_package(root / "scenarios") / "md_rec_002_standard")
            rows = [
                # task-relevant baseline sits inside the window
                row("2001-MD-REC-002-standard-A", "MD-REC-002", "coordinated",
                    scores={"metric.discovery": 0.7, "metric.gap": 0.7}),
                # floor control at the ceiling must not be read as task-relevant headroom
                # (metric.gap is minimised, so 0.0 is its best value)
                row("2001-MD-TRK-001-standard-B", "MD-TRK-001", "idle",
                    scores={"metric.discovery": 1.0, "metric.gap": 0.0}),
                # a scenario whose episode never reached a terminal is unusable, not zero
                row("2001-MD-REC-002-standard-B", "MD-REC-002", "sweep", complete=False,
                    scores={"metric.discovery": 0.7, "metric.gap": 0.7}),
            ]
            keys = {"2001-MD-REC-002-standard-A": "MD-REC-002",
                    "2001-MD-TRK-001-standard-B": "MD-TRK-001",
                    "2001-MD-REC-002-standard-B": "MD-REC-002"}
            summary = graded.analyse(rows, {"MD-REC-002": policies, "MD-TRK-001": policies},
                                     keys)
            self.assertEqual(summary["n_unusable"], 1)
            rec = summary["scenarios"]["MD-REC-002"]
            self.assertEqual(rec["d2_graded_verdict"], "pass")
            self.assertEqual(rec["headroom_band"], "window")
            trk = summary["scenarios"]["MD-TRK-001"]
            self.assertTrue(trk["best_is_floor_control"])
            self.assertEqual(trk["headroom_band"], "near_ceiling")
            self.assertEqual(summary["headroom_bands"],
                             {"below_window": 0, "window": 1, "near_ceiling": 1})
            self.assertEqual(summary["by_family"]["REC"]["in_window"], 1)
            self.assertEqual(summary["cases_without_policy"], [])
            self.assertEqual(summary["counts"]["binary_pass"], 0)

    def test_weight_policy_is_summarised_for_the_record(self):
        with tempfile.TemporaryDirectory() as folder:
            package = make_package(Path(folder) / "scenarios") / "md_rec_002_standard"
            policy = graded.scoring_policy(package)
            self.assertEqual(policy["weight_policy"], "normalized_sum_one")
            self.assertEqual(policy["aggregation_version"], "utility-v1")
            self.assertAlmostEqual(policy["weight_sum"], 1.0)
            self.assertEqual(policy["weights"]["metric.gap"]["direction"], "minimize")

    def test_missing_report_keeps_rows_unscored(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            rows = [row("c1", "MD-REC-002", "coordinated")]
            graded.cases_from_evidence(rows, root)
            self.assertEqual(rows[0]["scores"], {})


if __name__ == "__main__":
    unittest.main()

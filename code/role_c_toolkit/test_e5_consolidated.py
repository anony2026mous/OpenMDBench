"""Offline tests for the consolidated E5 summary.

The file must be reproducible from the artifacts alone, must state the failed criterion
without softening it, and must not invent fields the source data does not contain.
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

spec = importlib.util.spec_from_file_location('e5_consolidated_under_test',
                                              ROOT / 'e5_consolidated.py')
consolidated = importlib.util.module_from_spec(spec)
sys.modules['e5_consolidated_under_test'] = consolidated
spec.loader.exec_module(consolidated)

KEY = {"E5-01-a16a": "ie-03-surface-raid__llm-rl__s5101",
       "E5-02-f21c": "ie-08-island-strike__llm-rl__s5101"}
KAPPA = {
    "cases": [
        {"case_id": "ie-03-surface-raid__llm-rl__s5101", "kind": "hifi",
         "scenario": "IE-03-SURFACE-RAID", "seed": 5101, "score": 0.286,
         "outcome": "intruder_success", "machine_label": "planning", "dP": 0.483,
         "dE": 0.0, "dI": 0.207, "attribution_status": "complete", "replay_gate": True,
         "reference_scores": {"self_replay": 0.286, "reference_executor": 0.286,
                              "reference_planner": 0.769, "reference_full": 0.976},
         "frozen_plan_horizon": None},
        {"case_id": "ie-08-island-strike__llm-rl__s5101", "kind": "hifi",
         "scenario": "IE-08-ISLAND-STRIKE", "seed": 5101, "score": 0.265,
         "outcome": "intruder_success", "machine_label": "interface", "dP": -0.034,
         "dE": 0.001, "dI": 0.296, "attribution_status": "complete", "replay_gate": True,
         "reference_scores": {"self_replay": 0.265, "reference_executor": 0.266,
                              "reference_planner": 0.231, "reference_full": 0.529},
         "frozen_plan_horizon": {"last_recorded_decision_tick": 1040,
                                 "held_last_plan_calls_after_horizon": 14}},
    ],
    "n_cases": 2, "n_paired": 2, "all_replay_gates_passed": True,
    "all_attributions_complete": True,
    "machine_label_counts": {"planning": 1, "interface": 1},
    "cohen_kappa": 0.25, "agreement": 0.5,
    "confusion": {"planning": {"execution": 1}, "interface": {"balanced": 1}},
    "disagreements": [{"case_id": "ie-03-surface-raid__llm-rl__s5101",
                       "machine": "planning", "human": "execution"},
                      {"case_id": "ie-08-island-strike__llm-rl__s5101",
                       "machine": "interface", "human": "balanced"}],
    "success_criterion": {"kappa_at_least": 0.6, "disagreements_at_most": 2, "met": False},
}
ANNOTATION = (
    'packet_id,label,confidence,rationale\n'
    'E5-01-a16a,execution,2,"tick 28 之后没有射击"\n'
    'E5-02-f21c,balanced,2,"两层都有问题"\n'
)


def write_artifacts(root: Path) -> Path:
    (root / "annotation-final").mkdir(parents=True)
    (root / "annotation-final" / "KEY_DO_NOT_SHARE.json").write_text(
        json.dumps(KEY), encoding="utf-8")
    (root / "kappa_summary.json").write_text(json.dumps(KAPPA), encoding="utf-8")
    (root / "annotation_form_filled.csv").write_text(ANNOTATION, encoding="utf-8")
    for run, seeds in (("run-hifi-r1", (5101, 5102, 5103)), ("run-hifi-r2", (5104,))):
        for seed in seeds:
            case = f"ie-03-surface-raid__llm-rl__s{seed}"
            folder = root / "raw" / run / "episodes" / case
            folder.mkdir(parents=True)
            score = 0.286 if seed % 2 else 0.9
            (folder / "manifest.json").write_text(json.dumps({
                "status": "complete", "eligible_for_main_score": True,
                "case": {"scenario": "IE-03-SURFACE-RAID", "seed": seed},
                "defender_score": score,
                "terminal_result": {"outcome": "intruder_success" if score < 0.6
                                    else "defender_success"}}), encoding="utf-8")
    grid = root / "raw" / "grid-campaign"
    grid.mkdir(parents=True)
    (grid / "e5_grid_summary.json").write_text(json.dumps({
        "schema": "e5-grid-natural-failures@1",
        "seeds": [{"seed": 5201, "V0": 0.2333, "failure": True, "machine_label": "planning",
                   "replay_gate": True, "dP": 0.767, "dE": 0.067, "dI": -0.667},
                  {"seed": 5202, "V0": 0.9, "failure": False, "machine_label": None,
                   "replay_gate": True, "dP": 0.1, "dE": 0.0, "dI": 0.6}]}), encoding="utf-8")
    (grid / "seed-5201").mkdir()
    (grid / "seed-5201" / "summary.json").write_text(json.dumps(
        {"reports": {"original": {"V": 0.2333, "done": True, "steps": 81}}}), encoding="utf-8")
    return root


class ConsolidatedTests(unittest.TestCase):
    def test_states_the_failed_criterion_and_uses_only_real_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            root = write_artifacts(Path(folder))
            text = consolidated.render(root)
            # The criterion failed, and the file must say so in those words.
            self.assertIn('未达标', text)
            self.assertIn('0.250', text)
            self.assertIn('IE-03-SURFACE-RAID', text)
            self.assertIn('语义歧义', text)
            # grid carries no outcome field, so the file must not imply one.
            self.assertIn('未记录终局字段', text)
            self.assertIn('禁止', text)
            # Counts come from the data, not from a template constant.
            self.assertIn('2/2', text)
            self.assertIn('2 例', text)

    def test_missing_annotation_does_not_crash_and_is_visible(self):
        with tempfile.TemporaryDirectory() as folder:
            root = write_artifacts(Path(folder))
            (root / "annotation_form_filled.csv").unlink()
            text = consolidated.render(root)
            self.assertIn('人工标注回收 | 0/2', text)
            self.assertIn('人工标签分布：****', text)

    def test_failure_rate_counts_thresholded_episodes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = write_artifacts(Path(folder))
            hifi = consolidated.hifi_episodes(root)
            # Fixture scores: seeds 5101/5103 at 0.286, 5102/5104 at 0.9.
            self.assertEqual(len(hifi), 4)
            self.assertEqual(sum(1 for row in hifi if row['score'] < 0.6), 2)
            grid = consolidated.grid_episodes(root)
            self.assertTrue(grid[0]['failure'])
            self.assertEqual(grid[0]['steps'], 81)


if __name__ == '__main__':
    unittest.main()

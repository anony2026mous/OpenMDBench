"""Offline tests for the D1' prior-score validation."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location('d1prime_validate_under_test',
                                              ROOT / 'd1prime_validate.py')
validate_mod = importlib.util.module_from_spec(spec)
sys.modules['d1prime_validate_under_test'] = validate_mod
spec.loader.exec_module(validate_mod)


def frozen(rows):
    return {"schema": "d1prime-frozen@1",
            "rows": [{"public_id": key, "prior_score": value, "scores": {}}
                     for key, value in rows]}


class ValidationTests(unittest.TestCase):
    def test_perfectly_rank_correlated_data_is_supported(self):
        priors = [(f"S{index}", 1.0 + index * 0.2) for index in range(8)]
        scores = {f"S{index}": -0.5 + index * 0.1 for index in range(8)}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=6)
        self.assertEqual(summary["status"], "reported")
        self.assertAlmostEqual(summary["spearman_rho"], 1.0, places=6)
        self.assertTrue(summary["supported"])
        self.assertLess(summary["p_value"], 0.05)
        self.assertEqual(summary["direction"], "positive")

    def test_inverse_ranking_is_not_supported(self):
        priors = [(f"S{index}", 1.0 + index * 0.2) for index in range(8)]
        scores = {f"S{index}": 0.5 - index * 0.05 for index in range(8)}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=6)
        self.assertAlmostEqual(summary["spearman_rho"], -1.0, places=6)
        self.assertFalse(summary["supported"])
        self.assertEqual(summary["direction"], "negative")

    def test_too_few_pairs_is_reported_as_insufficient_not_as_a_result(self):
        priors = [("S1", 1.0), ("S2", 2.0), ("S3", 3.0)]
        scores = {"S1": 0.1, "S2": 0.2, "S3": 0.3}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=6)
        self.assertEqual(summary["status"], "insufficient_coverage")
        self.assertNotIn("spearman_rho", summary)
        self.assertEqual(summary["paired_scenarios"], 3)

    def test_missing_observed_values_are_listed_not_imputed(self):
        priors = [(f"S{index}", 1.0 + index * 0.1) for index in range(8)]
        scores = {f"S{index}": 0.1 * index for index in range(6)}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=6)
        self.assertEqual(summary["paired_scenarios"], 6)
        self.assertEqual(sorted(summary["missing_observed"]), ["S6", "S7"])

    def test_ties_use_average_ranks(self):
        self.assertEqual(validate_mod.rank([5.0, 5.0, 1.0, 3.0]), [3.5, 3.5, 1.0, 2.0])

    def test_short_scenario_keys_match_their_frozen_public_id(self):
        """A scores file may key on "IE-03" while the frozen table holds "IE-03-SURFACE-RAID"."""
        priors = [("IE-01-SINGLE-TARGET", 1.0), ("IE-03-SURFACE-RAID", 1.4),
                  ("IE-05-MULTI-AXIS", 3.0), ("IE-06-DECOY-MIXED", 2.6),
                  ("IE-07-CROSS-DOMAIN", 2.0), ("IE-08-ISLAND-STRIKE", 1.7)]
        scores = {"IE-01": 0.0, "IE-03": 0.1, "IE-05": 0.5, "IE-06": 0.4,
                  "IE-07": 0.25, "IE-08": 0.2}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=6)
        self.assertEqual(summary["status"], "reported")
        self.assertEqual(summary["paired_scenarios"], 6)
        self.assertAlmostEqual(summary["spearman_rho"], 1.0, places=6)

    def test_ambiguous_or_unknown_keys_are_reported_not_silently_dropped(self):
        priors = [("IE-01-SINGLE-TARGET", 1.0), ("IE-02-DUAL-THREAT", 2.0)]
        scores = {"IE-01": 0.1, "IE-02": 0.2, "TRK-99": 0.3}
        summary = validate_mod.validate(frozen(priors), scores, min_scenarios=1)
        self.assertEqual(summary["unmatched_keys"], ["TRK-99"])
        self.assertEqual(summary["paired_scenarios"], 2)

    def test_csv_and_json_sources_load_the_same_way(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            csv_path = root / "scores.csv"
            csv_path.write_text("scenario,composite\nS1,0.4\nS2,0.7\n", encoding="utf-8")
            json_path = root / "scores.json"
            json_path.write_text(json.dumps({"S1": 0.4, "S2": {"composite": 0.7}}),
                                 encoding="utf-8")
            self.assertEqual(validate_mod.load_scores(csv_path), {"S1": 0.4, "S2": 0.7})
            self.assertEqual(validate_mod.load_scores(json_path), {"S1": 0.4, "S2": 0.7})


if __name__ == '__main__':
    unittest.main()

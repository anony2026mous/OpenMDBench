"""Fast statistical/provenance tests; no model or simulation calls."""
import tempfile
import unittest
from pathlib import Path
from common import estimate, write, read
from e3_classify import rule, metrics, freeze


class Tests(unittest.TestCase):
    def test_paired_constant(self):
        result = estimate([.4] * 10)
        self.assertAlmostEqual(result["mean"], .4)
        self.assertTrue(all(abs(v-.4) < 1e-12 for v in result["ci95"]))

    def test_rule_observation_only(self):
        row = {"numeric": {"headings": [[-1, 0]] * 3, "positions": [[5, 18]] * 3}, "gold_real": False}
        self.assertEqual(rule(row), 1)
        row["gold_real"] = True
        self.assertEqual(rule(row), 1)
        row["numeric"]["headings"] = [[0, 0]] * 3
        self.assertEqual(rule(row), .5)

    def test_tied_auc(self):
        rows = [{"gold_real": g, "seed": s, "score": .5} for s in range(4) for g in [False, True]]
        result = metrics(rows, "score")
        self.assertEqual(result["auc"], .5)
        self.assertEqual(result["accuracy"], .5)
        self.assertEqual(result["n_seed_clusters"], 4)

    def test_invalid_outputs_count_as_errors(self):
        rows = [{"gold_real": g, "seed": s, "score": None} for s in range(4) for g in [False, True]]
        self.assertEqual(metrics(rows, "score")["accuracy"], 0)
        self.assertEqual(metrics(rows, "score", valid_only=True)["n"], 0)

    def test_no_fabricated_balanced_samples(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            with self.assertRaises(ValueError):
                freeze(p, p, 200)
            self.assertFalse(read(p / "dataset_audit.json")["eligible"])


if __name__ == "__main__":
    unittest.main()

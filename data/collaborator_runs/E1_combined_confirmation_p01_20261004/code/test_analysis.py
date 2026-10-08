"""Focused tests for postprocessing only; no engine or model requests."""
import unittest
import numpy as np
from analyze_final import bootstrap, contrast


class StatisticsTests(unittest.TestCase):
    def test_exact_constant_pair_difference(self):
        x = np.arange(10) / 20
        result = contrast(x + .1, x)
        self.assertAlmostEqual(result['mean'], .1)
        np.testing.assert_allclose(result['ci'], [.1, .1])

    def test_pair_alignment_is_preserved(self):
        x = np.arange(10) / 20
        paired = contrast(x, x)
        shuffled = contrast(x, x[::-1])
        self.assertEqual(paired['ci'], [0., 0.])
        self.assertGreater(shuffled['ci'][1]-shuffled['ci'][0], 0)

    def test_sensitivity_interval_is_wider(self):
        x = np.linspace(-.1, .2, 10)
        primary = bootstrap(x)
        wide = bootstrap(x, .05/8)
        self.assertLessEqual(wide['ci'][0], primary['ci'][0])
        self.assertGreaterEqual(wide['ci'][1], primary['ci'][1])

    def test_reproducible_bootstrap(self):
        x = np.linspace(-.1, .2, 10)
        self.assertEqual(bootstrap(x), bootstrap(x))

    def test_wrong_seed_count_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap([0]*9)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):
            bootstrap([0]*9+[float('nan')])


if __name__ == '__main__':
    unittest.main()

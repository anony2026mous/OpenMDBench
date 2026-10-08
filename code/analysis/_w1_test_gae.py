"""Numerical regression for bootstrapping at concatenated rollout boundaries."""
import unittest

import numpy as np

from ie_rl_train import compute_gae


class GaeTests(unittest.TestCase):
    def test_truncation_bootstraps_own_successor_without_cross_episode_recursion(self):
        advantage, returns = compute_gae(
            np.array([1.0, 2.0, 100.0]), np.array([10.0, 20.0, 50.0]),
            np.array([0.0, 1.0, 1.0]), np.array([0.0, 0.0, 1.0]),
            gamma=0.9, lam=0.8, next_values=np.array([20.0, 30.0, 999.0]))
        np.testing.assert_allclose(advantage, [15.48, 9.0, 50.0], atol=1e-5)
        np.testing.assert_allclose(returns, [25.48, 29.0, 100.0], atol=1e-5)

    def test_missing_truncation_successor_is_rejected(self):
        with self.assertRaises(ValueError):
            compute_gae(np.array([1.0]), np.array([2.0]), np.array([1.0]),
                        np.array([0.0]), gamma=0.9, lam=0.8)

    def test_true_terminal_does_not_bootstrap(self):
        advantage, returns = compute_gae(
            np.array([3.0]), np.array([7.0]), np.array([1.0]),
            np.array([1.0]), gamma=0.9, lam=0.8, last_value=123.0)
        np.testing.assert_allclose(advantage, [-4.0])
        np.testing.assert_allclose(returns, [3.0])


if __name__ == "__main__":
    unittest.main()

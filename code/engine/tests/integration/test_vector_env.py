"""Isolation and ordering contracts for batched local sessions."""

import numpy as np
from numpy.typing import NDArray
from openmdbench.envs import make_vector_env


def test_vector_batch_and_independent_reset() -> None:
    env = make_vector_env(("MD-REC-001", "MD-TRK-001"), seeds=(7, 11))
    observations: NDArray[np.float32]
    observations, _ = env.reset(seed=[7, 11])
    assert observations.shape == (2, 8)
    actions = np.array([[1.0, 0.0], [2.0, 90.0]], dtype=np.float32)
    advanced: NDArray[np.float32]
    advanced, _, _, _, _ = env.step(actions)
    reset: NDArray[np.float32]
    reset, _ = env.reset(
        seed=[7, None], options={"reset_mask": np.array([True, False], dtype=np.bool_)}
    )
    assert reset[0, 6] == 0.0
    np.testing.assert_array_equal(reset[1], advanced[1])
    env.close()


def test_parallel_order_does_not_change_session_results() -> None:
    scenario_ids = ("MD-REC-001", "MD-TRK-001")
    actions = np.array([[3.0, 15.0], [4.0, 120.0]], dtype=np.float32)
    forward = make_vector_env(scenario_ids, seeds=(17, 23))
    reverse = make_vector_env(tuple(reversed(scenario_ids)), seeds=(23, 17))
    forward.reset(seed=[17, 23])
    reverse.reset(seed=[23, 17])
    forward_result: NDArray[np.float32] = forward.step(actions)[0]
    reverse_result: NDArray[np.float32] = reverse.step(actions[::-1])[0]
    np.testing.assert_array_equal(forward_result[0], reverse_result[1])
    np.testing.assert_array_equal(forward_result[1], reverse_result[0])
    forward.close()
    reverse.close()

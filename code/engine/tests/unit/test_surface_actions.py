"""Tests for solver-specific surface action semantics."""

import math

import numpy as np
import pytest
from openmdbench.domains.surface.actions import (
    heading_to_rudder,
    validate_action_tensor_shape,
    validate_kinematic_actions,
    validate_mmg_actions,
)


def test_mmg_action_is_nps_and_rudder_radians() -> None:
    actions = np.array([[[2.0, 0.2]]], dtype=np.float32)
    np.testing.assert_allclose(validate_mmg_actions(actions), actions)


@pytest.mark.parametrize("rudder", [-0.31, 0.31, math.inf])
def test_mmg_rejects_illegal_rudder(rudder: float) -> None:
    with pytest.raises(ValueError):
        validate_mmg_actions(np.array([1.0, rudder]))


def test_kinematic_action_is_speed_and_heading() -> None:
    actions = np.array([[7.7, 359.0]])
    np.testing.assert_allclose(validate_kinematic_actions(actions), actions)


@pytest.mark.parametrize("heading", [-1.0, 360.0])
def test_kinematic_rejects_heading_outside_public_range(heading: float) -> None:
    with pytest.raises(ValueError):
        validate_kinematic_actions(np.array([1.0, heading]))


def test_heading_controller_converts_target_to_bounded_rudder() -> None:
    assert heading_to_rudder(90.0, 0.0) == pytest.approx(0.0)
    assert heading_to_rudder(0.0, 0.0) == pytest.approx(0.3)
    assert heading_to_rudder(180.0, 0.0) == pytest.approx(-0.3)


def test_phase_zero_action_shape_keeps_batch_and_entity_axes() -> None:
    validate_action_tensor_shape(np.zeros((4, 1, 2)), batch_size=4, entity_count=1)
    with pytest.raises(ValueError, match="shape"):
        validate_action_tensor_shape(np.zeros((4, 2)), batch_size=4, entity_count=1)

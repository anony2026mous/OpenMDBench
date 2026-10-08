import copy

from openmdbench.core.entities import Side
from openmdbench.envs import OpenMDBenchEnv
from openmdbench.policies import AD2EasyBlueAgent, AD2RedBaselineAgent


def _agents(env: OpenMDBenchEnv) -> tuple[AD2RedBaselineAgent, AD2EasyBlueAgent]:
    protected = (float(env._protected_point[0]), float(env._protected_point[1]))
    return AD2RedBaselineAgent(protected), AD2EasyBlueAgent((*protected, 100.0))


def _advance(env: OpenMDBenchEnv, red: AD2RedBaselineAgent, blue: AD2EasyBlueAgent) -> None:
    red_batch = red.act(env.red_observation())
    blue_batch = blue.act(env.public_observation(Side.BLUE))
    env.step_bilateral(blue_batch, env._validate_red_batch(red_batch))


def test_easy_checkpoint_restores_agent_and_future_events_exactly() -> None:
    continuous = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=31)
    continuous.reset(seed=31)
    red, blue = _agents(continuous)
    red.reset(continuous.red_observation(), 31)
    blue.reset(continuous.public_observation(Side.BLUE), 31)
    _advance(continuous, red, blue)
    _advance(continuous, red, blue)
    simulation = copy.deepcopy(continuous.export_state())
    agent_state = copy.deepcopy(red.snapshot())

    restored = OpenMDBenchEnv(scenario_id="MD-AD-002-EASY", seed=31)
    restored.reset(seed=31)
    restored.import_state(simulation)
    restored_red, restored_blue = _agents(restored)
    restored_red.restore(agent_state)

    _advance(continuous, red, blue)
    _advance(restored, restored_red, restored_blue)
    assert restored.export_state() == continuous.export_state()

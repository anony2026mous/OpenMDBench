"""CPU forward, persistence, and minimal PPO-update smoke tests."""
# mypy: disable-error-code="import-untyped,no-untyped-call"

from types import SimpleNamespace

import torch
from model.sim2sea_mlp_agent import MLPAgent
from torch.distributions import Normal


def _config(mode: str) -> SimpleNamespace:
    return SimpleNamespace(
        a_lr=1e-3,
        action_max=1.0,
        action_max_0=1.0,
        action_max_1=0.3,
        action_space=2,
        c_lr=1e-3,
        cls=False,
        context_len=2,
        device="cpu",
        mode=mode,
        n_embed=16,
        n_head=1,
        n_layer=1,
        obs_space=8,
        q_lr=1e-3,
        use_bev=False,
        use_mask=False,
    )


def test_actor_critic_forward_without_bev_and_minimal_ppo_update() -> None:
    actor = MLPAgent(_config("actor"))
    critic = MLPAgent(_config("critic"))
    observations = torch.randn(4, 2, 8)

    means = actor(observations, None)
    values = critic(observations, None)
    assert means.shape == (4, 2)
    assert values.shape == (4, 1)

    distribution = Normal(means, torch.ones_like(means))
    actions = distribution.sample()
    old_log_prob = distribution.log_prob(actions).sum(-1).detach()
    advantages = torch.tensor([1.0, -0.5, 0.25, 0.75])
    ratio = (distribution.log_prob(actions).sum(-1) - old_log_prob).exp()
    actor_loss = -torch.minimum(
        ratio * advantages, torch.clamp(ratio, 0.8, 1.2) * advantages
    ).mean()
    critic_loss = torch.nn.functional.mse_loss(values.squeeze(-1), advantages)

    actor.optimizer.zero_grad()
    critic.optimizer.zero_grad()
    actor_loss.backward()
    critic_loss.backward()
    actor.optimizer.step()
    critic.optimizer.step()
    assert torch.isfinite(actor_loss)
    assert torch.isfinite(critic_loss)


def test_actor_and_critic_save_and_load_separately(tmp_path: object) -> None:
    actor = MLPAgent(_config("actor"))
    critic = MLPAgent(_config("critic"))
    actor_path = str(tmp_path) + "/actor.pt"
    critic_path = str(tmp_path) + "/critic.pt"
    torch.save(actor.state_dict(), actor_path)
    torch.save(critic.state_dict(), critic_path)

    restored_actor = MLPAgent(_config("actor"))
    restored_critic = MLPAgent(_config("critic"))
    restored_actor.load_state_dict(torch.load(actor_path, weights_only=True))
    restored_critic.load_state_dict(torch.load(critic_path, weights_only=True))
    assert restored_actor.action_dim == 2
    assert restored_critic.action_dim == 1

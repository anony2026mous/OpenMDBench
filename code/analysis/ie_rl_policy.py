"""One network, direct actions: the policy that drives the RL arm.

Design contract (fixed by the requirement "the network directly outputs the
concrete actions of the UAVs and USVs, no other layer"):

    ONE network  ->  per-slot heading + per-slot speed + per-slot fire target
                     for every friendly unit, in one forward pass
    env          ->  converts those numbers into engine commands
                     (navigation + fire_weapon).  No goal layer, no executor,
                     no rule fallback, no second network.

The value function is a **head on the same trunk**, not a second network; PPO
needs a critic and this keeps the "one network decides" property intact.

Action encoding (chosen for learning quality, not as a decision layer):

    heading   two outputs per slot, squashed by tanh, read as an absolute
              direction via ``atan2(sin, cos)``.  Emitting a raw angle in
              [0, 360) would put a discontinuity at the 0/360 wrap; the (sin,
              cos) form carries exactly the same information (an absolute
              heading) without that cliff.  Returned as ``heading_xy``.
    speed     one output per slot, tanh mapped to ``[0, 1]`` = an absolute
              fraction of that class's maximum speed in m/s.  Returned as
              ``speed``.
    fire      masked categorical over {hold, target_1 .. target_K}; the mask
              only removes choices the engine would reject.

Canonical action dict consumed by ``ie_rl_env.submit_action``::

    {"heading_xy": (N, 2) float32,
     "speed":      (N,)   float32,   # fraction of the class max
     "fire":       (N,)   int64}     # 0 = hold, j+1 = target slot j

``heading_deg`` is also returned, but purely as a derived read-out for tests and
logging -- the environment decodes ``heading_xy`` itself.

Two implementations, one parameter layout: rollout workers evaluate in numpy
(no torch, no GPU) while the trainer optimises a torch module on the GPU.  A
parity test asserts they agree numerically -- without it a worker could act
under different weights than the trainer updates, and the run would be
meaningless while still producing a plausible-looking learning curve.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

HIDDEN = 256
# Initial log-std for the continuous heads.
#
# Measured failure: with 0.0 (std = 1.0) the heading head drew ``tanh(mu + N(0,1))``
# and read it back through ``atan2``, i.e. a **near-uniform direction every
# decision** -- the commanded course was essentially random, so the policy could
# not execute any coherent manoeuvre and the return stayed flat for 13 iterations.
# Worse, ``log_std`` never moved: after those 13 iterations the mean was 0.0031
# (sigma = 1.003), because the entropy bonus rewards larger sigma and, with three
# continuous components per slot now under it (48 in total), it simply balanced the
# policy gradient.  -1.5 gives sigma = 0.22, about +-12 degrees of heading jitter:
# explorable, but a course can actually be held.
LOG_STD_INIT = -1.5
HEADS = ("trunk0", "trunk1", "heading", "speed", "fire", "value")
# 2 heading components + 1 speed component per slot
LOG_STD_PER_UNIT = 3


def theta_shapes(obs_dim: int, num_units: int, num_fire: int,
                 hidden: int = HIDDEN) -> dict[str, tuple[int, ...]]:
    return {
        "trunk0.w": (obs_dim, hidden), "trunk0.b": (hidden,),
        "trunk1.w": (hidden, hidden), "trunk1.b": (hidden,),
        "heading.w": (hidden, 2 * num_units), "heading.b": (2 * num_units,),
        "speed.w": (hidden, num_units), "speed.b": (num_units,),
        "fire.w": (hidden, num_units * num_fire), "fire.b": (num_units * num_fire,),
        "value.w": (hidden, 1), "value.b": (1,),
        "log_std": (LOG_STD_PER_UNIT * num_units,),
    }


def init_theta(rng: np.random.Generator, obs_dim: int, num_units: int,
               num_fire: int, hidden: int = HIDDEN) -> dict[str, np.ndarray]:
    theta: dict[str, np.ndarray] = {}
    for name, shape in theta_shapes(obs_dim, num_units, num_fire, hidden).items():
        if name == "log_std":
            theta[name] = np.full(shape, LOG_STD_INIT, dtype=np.float32)
        elif name.endswith(".b"):
            theta[name] = np.zeros(shape, dtype=np.float32)
        else:
            limit = 1.0 / np.sqrt(shape[0])
            theta[name] = rng.uniform(-limit, limit, shape).astype(np.float32)
    return theta


def numpy_trunk(theta: dict[str, np.ndarray], obs: np.ndarray) -> np.ndarray:
    h = np.tanh(obs @ theta["trunk0.w"] + theta["trunk0.b"])
    return np.tanh(h @ theta["trunk1.w"] + theta["trunk1.b"])


def numpy_forward(theta: dict[str, np.ndarray], obs: np.ndarray,
                  num_units: int, num_fire: int) -> dict[str, np.ndarray]:
    h = numpy_trunk(theta, obs)
    return {
        "heading": (h @ theta["heading.w"] + theta["heading.b"]).reshape(num_units, 2),
        "speed": h @ theta["speed.w"] + theta["speed.b"],
        "fire": (h @ theta["fire.w"] + theta["fire.b"]).reshape(num_units, num_fire),
        "value": (h @ theta["value.w"] + theta["value.b"]).reshape(()),
    }


def _logp_tanh(mean: np.ndarray, pre: np.ndarray, squashed: np.ndarray,
               std: np.ndarray) -> np.ndarray:
    """log density of ``tanh(N(mean, std^2))`` evaluated at ``tanh(pre)``.

    ``mean`` is a required argument, not an optional refinement: without it the
    density is evaluated at ``pre`` instead of at ``pre - mean``, which is only
    correct by accident when the head's output happens to be zero.  The
    ``log(1 - tanh(x)^2)`` term is the tanh change-of-variables.
    """
    var = std ** 2
    base = -0.5 * ((pre - mean) ** 2 / var + np.log(2 * np.pi * var))
    return base - np.log(np.maximum(1.0 - squashed ** 2, 1e-6))


def numpy_sample(
    theta: dict[str, np.ndarray], obs: np.ndarray, fire_mask: np.ndarray,
    rng: np.random.Generator, num_fire: int, *, deterministic: bool = False,
    slot_mask: np.ndarray | None = None,
) -> tuple[dict[str, np.ndarray], float, float, dict[str, np.ndarray]]:
    """Sample (or take the mode of) the policy.

    ``slot_mask`` (1.0 for live slots) scales every per-slot log-prob term so
    padded or dead slots contribute nothing to the objective -- their outputs
    cannot affect the world, so including them only injects noise.
    """
    num_units = fire_mask.shape[0]
    out = numpy_forward(theta, obs, num_units, num_fire)
    std = np.exp(theta["log_std"]).reshape(num_units, LOG_STD_PER_UNIT)
    active = (np.ones(num_units, dtype=np.float32) if slot_mask is None
              else np.asarray(slot_mask, dtype=np.float32).reshape(-1))

    if deterministic:
        head_xy = np.tanh(out["heading"])
        heading = np.arctan2(head_xy[:, 0], head_xy[:, 1])
        speed_frac = (np.tanh(out["speed"]) + 1.0) / 2.0
        choice = np.argmax(np.where(fire_mask, out["fire"], -1e9), axis=1)
        return ({"heading_xy": head_xy.astype(np.float32),
                 "speed": speed_frac.astype(np.float32),
                 # derived, for tests/logging only -- the env reads heading_xy
                 "heading_deg": (np.degrees(heading) % 360.0).astype(np.float32),
                 "fire": choice.astype(np.int64)},
                0.0, float(out["value"]), out)

    eps = rng.standard_normal((num_units, LOG_STD_PER_UNIT)).astype(np.float32)
    head_pre = out["heading"] + std[:, :2] * eps[:, :2]
    speed_pre = out["speed"] + std[:, 2] * eps[:, 2]
    head_xy = np.tanh(head_pre)
    speed_frac = (np.tanh(speed_pre) + 1.0) / 2.0

    logits = np.where(fire_mask, out["fire"], -1e9)
    logits = logits - logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs /= probs.sum(axis=1, keepdims=True)
    choice = np.array([rng.choice(num_fire, p=probs[i]) for i in range(num_units)],
                      dtype=np.int64)

    logprob = float((_logp_tanh(out["heading"], head_pre, head_xy,
                                std[:, :2]).sum(axis=1) * active).sum())
    logprob += float((_logp_tanh(out["speed"], speed_pre, np.tanh(speed_pre),
                                 std[:, 2]) * active).sum())
    logprob += float((np.log(probs[np.arange(num_units), choice] + 1e-12)
                      * active).sum())
    heading = np.arctan2(head_xy[:, 0], head_xy[:, 1])
    return ({"heading_xy": head_xy.astype(np.float32),
             "speed": speed_frac.astype(np.float32),
             # derived, for tests/logging only -- the env reads heading_xy
             "heading_deg": (np.degrees(heading) % 360.0).astype(np.float32),
             "fire": choice}, logprob, float(out["value"]), out)


# ---------------------------------------------------------------------------
# torch implementation (trainer side) -- same layout, same names
# ---------------------------------------------------------------------------
def build_torch_policy(obs_dim: int, num_units: int, num_fire: int,
                       hidden: int = HIDDEN):
    import torch
    import torch.nn as nn

    class TorchPolicy(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.num_units = num_units
            self.num_fire = num_fire
            self.trunk0 = nn.Linear(obs_dim, hidden)
            self.trunk1 = nn.Linear(hidden, hidden)
            self.heading = nn.Linear(hidden, 2 * num_units)
            self.speed = nn.Linear(hidden, num_units)
            self.fire = nn.Linear(hidden, num_units * num_fire)
            self.value = nn.Linear(hidden, 1)
            self.log_std = nn.Parameter(
                torch.full((LOG_STD_PER_UNIT * num_units,), LOG_STD_INIT))

        def trunk(self, obs):
            return torch.tanh(self.trunk1(torch.tanh(self.trunk0(obs))))

        def distribution(self, obs, fire_mask):
            h = self.trunk(obs)
            std = torch.exp(self.log_std).view(-1, LOG_STD_PER_UNIT)
            logits = self.fire(h).view(-1, self.num_units, self.num_fire)
            logits = logits.masked_fill(~fire_mask, -1e9)
            return {
                "heading": self.heading(h).view(-1, self.num_units, 2),
                "speed": self.speed(h),
                "fire_logits": logits,
                "value": self.value(h).squeeze(-1),
                "std": std,
            }

    return TorchPolicy()


def load_theta_into_torch(model, theta: dict[str, np.ndarray]) -> None:
    import torch
    with torch.no_grad():
        for head in HEADS:
            layer = getattr(model, head)
            layer.weight.copy_(torch.from_numpy(theta[f"{head}.w"].T.copy()))
            layer.bias.copy_(torch.from_numpy(theta[f"{head}.b"].copy()))
        model.log_std.copy_(torch.from_numpy(theta["log_std"].copy()))


def export_theta_from_torch(model) -> dict[str, np.ndarray]:
    import torch
    out: dict[str, np.ndarray] = {}
    with torch.no_grad():
        for head in HEADS:
            layer = getattr(model, head)
            out[f"{head}.w"] = layer.weight.detach().cpu().numpy().T.astype(np.float32)
            out[f"{head}.b"] = layer.bias.detach().cpu().numpy().astype(np.float32)
        out["log_std"] = model.log_std.detach().cpu().numpy().astype(np.float32)
    return out


def save_theta(path: Path, theta: dict[str, np.ndarray],
               meta: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(theta)
    if meta is not None:
        payload[META_KEY] = pack_meta(meta)
    np.savez(path, **payload)


def load_theta(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


# ---------------------------------------------------------------------------
# Checkpoint provenance.
#
# A policy's numbers are only interpretable together with the environment it was
# trained in, and two of those settings can be flipped at evaluation time without
# any error being raised:
#
#   * ``speed_source`` -- ``legacy_tags`` scales the speed action by the rule
#     executor's 40/8 table while ``catalog`` scales it by the platform's real
#     80/10 limit, so the same weights command twice the speed under one of them;
#   * ``goal_features`` -- whether the trunk's input includes the plan block.
#
# Both were read from *defaults on the evaluation side* that did not match the
# training side, and the failure mode is silent: the arm merely "happens to score
# lower", and it is exactly the arm an ablation rests on.  Measured once already:
# ``theta_rl_legacy2`` (trained with ``legacy_tags``) was evaluated with
# ``catalog`` and the whole batch had to be discarded.
#
# So the settings travel WITH the weights.  ``_meta`` is a JSON string stored as a
# 0-d numpy array: it survives ``np.savez``/``np.load`` without pickle, and every
# reader of a theta dict here addresses weights by explicit key, so the extra entry
# is inert for the forward pass and the torch loaders.
# ---------------------------------------------------------------------------
META_KEY = "_meta"

#: Which settings must agree between the training run and the evaluation run.
META_FIELDS = ("speed_source", "goal_features", "obs_dim", "decision_interval",
               "num_units", "num_fire_choices", "log_std_init", "tag",
               "train_seed_base", "train_seed_span", "scenarios",
               "rollout_semantics")


def pack_meta(meta: dict) -> np.ndarray:
    """Serialise provenance into a numpy scalar array (no pickle)."""
    import json
    clean = {str(k): (list(v) if isinstance(v, (list, tuple)) else v)
             for k, v in dict(meta).items()}
    return np.asarray(json.dumps(clean, ensure_ascii=False, sort_keys=True))


def read_meta(theta: dict) -> dict:
    """Provenance recorded in the checkpoint, or ``{}`` when it has none.

    An **empty** result means "this checkpoint predates provenance" -- callers must
    not treat it as agreement with their own defaults.
    """
    import json
    raw = theta.get(META_KEY)
    if raw is None:
        return {}
    try:
        text = raw.item() if hasattr(raw, "item") else raw
        parsed = json.loads(str(text))
    except Exception:  # noqa: BLE001
        return {}
    return parsed if isinstance(parsed, dict) else {}

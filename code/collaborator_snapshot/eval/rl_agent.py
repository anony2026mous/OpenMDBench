"""RL arm adapter: drives a session with a trained PPO policy.

Why an adapter instead of a separate evaluation script
-----------------------------------------------------
The four-arm comparison is only valid if every arm is scored by the *same* code.
This class therefore implements the same ``__call__(session) -> dict`` protocol
as ``PureLLMAgentV2`` / ``AgentV2``, so ``run_episode.py --planner rl`` reuses the
identical scorecard, fire-verdict normalisation, loss attribution and logging.
A bespoke RL evaluation script would silently diverge from that pipeline.

Control level is the whole point: the network's output **is** the action.  Per
unit it emits an absolute heading, an absolute speed and an optional fire
target; there is no goal layer, no executor, no rule fallback and no second
network.  This module only bridges that output to the engine's two message
types (see ``ie_rl_env.submit_action``).

Inference is numpy (see ``ie_rl_policy``) so this runs in the engine venv without
torch, which is also how the rollout workers run.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ie_rl_env import IERlEnv  # noqa: E402
from ie_rl_policy import load_theta, numpy_sample, read_meta  # noqa: E402


def _base_obs_dim(public_id: str) -> int:
    """Observation size of the pre-lead-feature layout for this scenario.

    Cheap to compute and independent of the checkpoint: it is the 6-wide pair
    block, which is what every checkpoint trained before the lead features used.
    """
    probe = IERlEnv(public_id, lead_features=False)
    try:
        return probe.observation_size
    finally:
        probe.close()


def _resolve_speed_source(explicit: Optional[str], meta: Dict[str, Any],
                          default: str) -> tuple[str, str]:
    """(speed_source, where it came from).

    Kept as a free function so the RL executor resolves it the same way: two
    copies of this precedence is exactly how the convention drifted apart in the
    first place.
    """
    if explicit:
        value, origin = str(explicit), "argument"
    elif meta.get("speed_source") in ("catalog", "legacy_tags"):
        value, origin = str(meta["speed_source"]), "checkpoint_meta"
    elif os.environ.get("RL_SPEED_SOURCE"):
        value, origin = str(os.environ["RL_SPEED_SOURCE"]), "environment"
    else:
        value, origin = default, "guessed_default"
    if value not in ("catalog", "legacy_tags"):
        raise ValueError(f"RL_SPEED_SOURCE must be 'catalog' or 'legacy_tags', "
                         f"got {value!r} (from {origin})")
    return value, origin


class RLAgentV2:
    """Trained-policy controller with the harness' agent protocol."""

    def __init__(
        self,
        public_id: str,
        theta_path: str | os.PathLike,
        *,
        faction_id: str = "coalition.defender",
        decision_interval: int = 5,
        deterministic: bool = True,
        seed: int = 7,
        name: str = "defender.rl",
        speed_source: Optional[str] = None,
    ) -> None:
        self.public_id = public_id
        self.faction_id = faction_id
        self.decision_interval = max(1, int(decision_interval))
        self.deterministic = bool(deterministic)
        self.name = name
        self._theta = load_theta(Path(theta_path))
        self.theta_path = Path(theta_path)
        # The observation layout must match the one the checkpoint was trained on.
        # The pair block grew from 6 to 8 features when the lead-point bearing was
        # added, and it is 86% of the observation, so the two are not
        # interchangeable: feeding an 8-wide observation to a 6-wide checkpoint
        # fails at the first matmul.  The checkpoint's own ``trunk0.w`` says which
        # layout it expects, so the variant is inferred rather than assumed --
        # otherwise every checkpoint trained before the change becomes
        # unevaluatable, and "the old run cannot be scored" reads like a result.
        self.lead_features = int(self._theta["trunk0.w"].shape[0]) > _base_obs_dim(
            self.public_id)
        # Diagnostic hook: set RL_SLOT_SHUFFLE=<seed> to relabel the slots and
        # measure whether the policy is genuinely slot-symmetric (see IERlEnv).
        raw_shuffle = os.environ.get("RL_SLOT_SHUFFLE")
        self.slot_shuffle_seed = int(raw_shuffle) if raw_shuffle else None
        # Which speed envelope the speed action is scaled by.  Must be pinned to the
        # SAME convention on both sides of an executor ablation -- the rule
        # executor's tag table gives air units 40 m/s while the catalog says 80
        # (see ARM5_LLM_RL_EXECUTOR_DESIGN.md §3.3).
        #
        # Resolution order is explicit-argument -> checkpoint provenance -> env var
        # -> default, and WHICH ONE WON is recorded, because the failure this
        # replaces was silent: `theta_rl_legacy2` was trained with `legacy_tags`
        # and evaluated through this file's `catalog` default, so the same weights
        # commanded twice the speed and a whole batch had to be thrown away.  A
        # "guessed" provenance in the report is the signal that the row cannot be
        # trusted until the convention is pinned.
        self.speed_source, self.speed_source_provenance = _resolve_speed_source(
            speed_source, read_meta(self._theta), "catalog")
        if self.speed_source not in ("catalog", "legacy_tags"):
            raise ValueError(f"RL_SPEED_SOURCE must be 'catalog' or 'legacy_tags', "
                             f"got {self.speed_source!r}")
        self._rng = np.random.default_rng(seed)
        self._env: Optional[IERlEnv] = None
        self._last_tick = None
        self.stats: Dict[str, Any] = {
            "name": name, "faction_id": faction_id,
            "decisions": 0, "fires_submitted": 0,
        }

    # ------------------------------------------------------------------
    def _ensure(self, session) -> IERlEnv:
        if self._env is None:
            env = IERlEnv(self.public_id, seed=self._rng.integers(1 << 30),
                          decision_interval=self.decision_interval,
                          lead_features=self.lead_features,
                          slot_shuffle_seed=self.slot_shuffle_seed,
                          speed_source=self.speed_source)
            env.attach(session)
            self._env = env
        return self._env

    def __call__(self, session) -> Dict[str, Any]:
        env = self._ensure(session)
        tick = int(session.world_view.tick)
        # Decide once per ``decision_interval``; the persistent navigation
        # command remains in force between decisions, exactly like the
        # pure-LLM arm's plan interval.
        if self._last_tick is not None and tick - self._last_tick < self.decision_interval:
            return {"tick": tick, "submit_result": None,
                    "executor": {"fires": [], "submitted": 0,
                                 "safe_mode": False, "fallback": False,
                                 "masked": 0}}
        obs = env.observe()
        mask = env.fire_mask()
        action, _logprob, _value, _ = numpy_sample(
            self._theta, obs, mask, self._rng, env.num_fire_choices,
            deterministic=self.deterministic)
        fire_records, submitted = env.submit_action(action)
        self._last_tick = tick
        self.stats["decisions"] += 1
        self.stats["fires_submitted"] += len(fire_records)
        return {
            "tick": tick,
            "submit_result": None,
            "executor": {
                "fires": fire_records,
                "submitted": submitted,
                "safe_mode": False,
                "fallback": False,
                "masked": 0,
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """Harness stats.

        ``planner`` must be a **dict**, matching ``AgentV2``/``PureLLMAgentV2``:
        ``run_episode``'s report assembly does
        ``(planner_stats.get("planner") or {}).get("parse_failures")``, so a
        string here raised ``AttributeError: 'str' object has no attribute
        'get'`` at the very end of every episode.  That abort marked the episode
        ``aborted`` and forced the scorecard's terminal layer to 0.0, silently
        depressing the RL arm's score on every run.
        """
        return {
            "name": self.name,
            "faction_id": self.faction_id,
            "planner": {
                "planner": "rl",
                "theta": str(self.theta_path),
                "plan_calls": self.stats["decisions"],
                # the RL policy has no JSON plan and no rule fallback, so these
                # are real zeros rather than "unknown"
                "parse_failures": 0,
                "fallback_count": 0,
                "stale_plan_reuse": 0,
                "deterministic": self.deterministic,
                # Provenance: the score is only interpretable together with the
                # sampling mode and the speed convention it was measured under.
                "speed_source": self.speed_source,
                # "guessed_default" means nothing pinned it: the row is only usable
                # if that guess happens to match the training run.
                "speed_source_provenance": self.speed_source_provenance,
                "checkpoint_meta": read_meta(self._theta),
                "observation_size": (int(self._theta["trunk0.w"].shape[0])),
            },
            "decisions": self.stats["decisions"],
            "fires_submitted": self.stats["fires_submitted"],
        }
